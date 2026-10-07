"""
OpenAI service module.

Responsibility:
- Interact with OpenAI Vision API to analyze habit evidence images.
"""

import base64
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app
import openai
from openai import OpenAI

from app.config import get_image_validation_provider, is_openai_configured

VALIDATION_NOT_CONFIGURED_CODE = "validation_not_configured"
VALIDATION_PROVIDER_UNAVAILABLE_CODE = "validation_provider_unavailable"
VALIDATION_AUTH_ERROR_CODE = "validation_auth_error"
VALIDATION_QUOTA_EXCEEDED_CODE = "validation_quota_exceeded"
SUPPORTED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


class ValidationUnavailableError(RuntimeError):
    """Raised when photo validation is unavailable for operational reasons."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def _normalize_mime_type(mime_type: str | None) -> str:
    if mime_type is None:
        return "image/jpeg"

    normalized = mime_type.strip().lower()
    if normalized not in SUPPORTED_IMAGE_MIME_TYPES:
        raise ValueError("mime_type must be image/jpeg, image/png, or image/webp.")

    return "image/jpeg" if normalized == "image/jpg" else normalized


def _sanitize_base64_payload(image_base64: str) -> str:
    normalized = "".join(image_base64.strip().split())
    if not normalized:
        raise ValueError("image (base64) is required.")

    try:
        decoded = base64.b64decode(normalized, validate=True)
    except ValueError as exc:
        raise ValueError("image must be valid base64.") from exc

    if len(decoded) > MAX_IMAGE_BYTES:
        raise ValueError("image exceeds the 10MB validation limit.")

    return normalized


def analyze_habit_image(habit_name: str, image_base64: str, mime_type: str | None = None) -> dict:
    """Analyze an image using OpenAI Vision to validate a habit.

    Args:
        habit_name: Name of the habit to validate (e.g. "Hacer ejercicio").
        image_base64: Base64-encoded image string.

    Returns:
        dict with keys: valido (bool), razon (str), confianza (float).
    """
    provider = get_image_validation_provider(current_app.config)
    if provider is None:
        raise ValidationUnavailableError(
            "La validación de fotos no está disponible en este entorno.",
            VALIDATION_NOT_CONFIGURED_CODE,
        )

    normalized_mime_type = _normalize_mime_type(mime_type)
    normalized_image_base64 = _sanitize_base64_payload(image_base64)
    prompt = (
        "Eres un sistema que valida evidencia visual de hábitos.\n\n"
        f"Hábito: {habit_name}\n\n"
        "Analiza la imagen y responde SOLO en JSON válido con este formato:\n"
        '{\n'
        '  "valido": true o false,\n'
        '  "razon": "explicación breve en español",\n'
        '  "confianza": número entre 0 y 1\n'
        '}\n\n'
        "Reglas:\n"
        "- Determina si la imagen muestra evidencia razonable de que la persona "
        "está realizando o ha realizado el hábito indicado.\n"
        "- Sé flexible pero honesto. Si la imagen no tiene relación, marca como inválido.\n"
        "- Responde ÚNICAMENTE con el JSON, sin texto adicional."
    )

    if provider == "gemini":
        raw_content = _request_gemini_image_analysis(
            prompt,
            normalized_image_base64,
            normalized_mime_type,
            str(current_app.config.get("GEMINI_API_KEY") or "").strip(),
        )
        return _parse_ai_json_response(raw_content)

    api_key = str(current_app.config.get("OPENAI_API_KEY") or "").strip()
    try:
        client = OpenAI(api_key=api_key, timeout=20.0)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{normalized_mime_type};base64,{normalized_image_base64}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            max_tokens=300,
            temperature=0.2,
        )
    except openai.AuthenticationError as exc:
        current_app.logger.exception("Habit validation auth error.")
        raise ValidationUnavailableError(
            "La llave de OpenAI es inválida o ha sido revocada.",
            VALIDATION_AUTH_ERROR_CODE,
        ) from exc
    except openai.RateLimitError as exc:
        current_app.logger.exception("Habit validation rate limit or quota exceeded.")
        raise ValidationUnavailableError(
            "Se han agotado los créditos o la cuota de OpenAI.",
            VALIDATION_QUOTA_EXCEEDED_CODE,
        ) from exc
    except Exception as exc:
        current_app.logger.exception("Habit validation provider call failed.")
        raise ValidationUnavailableError(
            "La validación de fotos no está disponible temporalmente.",
            VALIDATION_PROVIDER_UNAVAILABLE_CODE,
        ) from exc

    raw_content = response.choices[0].message.content
    if isinstance(raw_content, list):
        raw = "".join(
            chunk.get("text", "")
            for chunk in raw_content
            if isinstance(chunk, dict) and chunk.get("type") == "text"
        ).strip()
    else:
        raw = str(raw_content or "").strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Remove first and last lines (``` markers)
        lines = [line for line in lines if not line.strip().startswith("```")]
        raw = "\n".join(lines)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        current_app.logger.warning("Habit validation provider returned invalid JSON.")
        raise ValidationUnavailableError(
            "La validación de fotos no está disponible temporalmente.",
            VALIDATION_PROVIDER_UNAVAILABLE_CODE,
        ) from exc

    return {
        "valido": bool(result.get("valido", False)),
        "razon": str(result.get("razon", "Sin razón proporcionada.")),
        "confianza": float(result.get("confianza", 0.0)),
    }


def _request_gemini_image_analysis(
    prompt: str,
    image_base64: str,
    mime_type: str,
    api_key: str,
) -> str:
    response_schema = {
        "type": "object",
        "properties": {
            "valido": {"type": "boolean"},
            "razon": {"type": "string"},
            "confianza": {"type": "number"},
        },
        "required": ["valido", "razon", "confianza"],
    }
    request_body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": image_base64,
                        }
                    },
                ]
            },
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
            "maxOutputTokens": 300,
            "thinkingConfig": {
                "thinkingBudget": 0,
            },
        },
    }
    request = Request(
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.5-flash-lite:generateContent",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60.0) as response:
            response_data = json.loads(response.read())
    except HTTPError as exc:
        try:
            error_response = json.loads(exc.read().decode("utf-8"))
            provider_message = str(
                error_response.get("error", {}).get("message", "")
            ).replace(api_key, "[redacted]")[:300]
        except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
            provider_message = ""

        if exc.code in {400, 401, 403}:
            code = VALIDATION_AUTH_ERROR_CODE
            message = "La llave de Gemini es inválida o no tiene acceso al modelo."
        elif exc.code == 429:
            code = VALIDATION_QUOTA_EXCEEDED_CODE
            message = "Se han agotado los créditos o la cuota de Gemini."
        else:
            code = VALIDATION_PROVIDER_UNAVAILABLE_CODE
            message = "La validación de fotos no está disponible temporalmente."
        current_app.logger.warning(
            "Gemini image validation returned HTTP %s: %s",
            exc.code,
            provider_message or "no provider detail",
        )
        raise ValidationUnavailableError(message, code) from exc
    except (URLError, TimeoutError, OSError) as exc:
        current_app.logger.warning("Gemini image validation request failed.")
        raise ValidationUnavailableError(
            "La validación de fotos no está disponible temporalmente.",
            VALIDATION_PROVIDER_UNAVAILABLE_CODE,
        ) from exc
    except json.JSONDecodeError as exc:
        current_app.logger.warning("Gemini image validation returned invalid response JSON.")
        raise ValidationUnavailableError(
            "La validación de fotos no está disponible temporalmente.",
            VALIDATION_PROVIDER_UNAVAILABLE_CODE,
        ) from exc

    try:
        parts = response_data["candidates"][0]["content"]["parts"]
        return "".join(str(part["text"]) for part in parts if "text" in part)
    except (KeyError, IndexError, TypeError) as exc:
        current_app.logger.warning("Gemini image validation response did not contain candidate text.")
        raise ValidationUnavailableError(
            "La validación de fotos no está disponible temporalmente.",
            VALIDATION_PROVIDER_UNAVAILABLE_CODE,
        ) from exc


def _parse_ai_json_response(raw_content: object) -> dict:
    if isinstance(raw_content, list):
        raw = "".join(
            chunk.get("text", "")
            for chunk in raw_content
            if isinstance(chunk, dict) and chunk.get("type") == "text"
        ).strip()
    else:
        raw = str(raw_content or "").strip()

    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        raw = "\n".join(lines)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        current_app.logger.warning("Habit validation provider returned invalid JSON.")
        raise ValidationUnavailableError(
            "La validación no está disponible temporalmente.",
            VALIDATION_PROVIDER_UNAVAILABLE_CODE,
        ) from exc

    return {
        "valido": bool(result.get("valido", False)),
        "razon": str(result.get("razon", "Sin razón proporcionada.")),
        "confianza": float(result.get("confianza", 0.0)),
    }


def analyze_habit_text(habit_name: str, text_content: str) -> dict:
    """Analyze text using OpenAI to validate a habit.

    Returns:
        dict with keys: valido (bool), razon (str), confianza (float).
    """
    if not is_openai_configured(current_app.config):
        raise ValidationUnavailableError(
            "La validación de texto no está disponible en este entorno.",
            VALIDATION_NOT_CONFIGURED_CODE,
        )

    api_key = str(current_app.config.get("OPENAI_API_KEY") or "").strip()
    prompt = (
        "Eres un sistema que valida evidencia textual de hábitos.\n\n"
        f"Hábito: {habit_name}\n\n"
        f"Texto del usuario:\n{text_content}\n\n"
        "Analiza el texto y responde SOLO en JSON válido con este formato:\n"
        "{\n"
        '  "valido": true o false,\n'
        '  "razon": "explicación breve en español",\n'
        '  "confianza": número entre 0 y 1\n'
        "}\n\n"
        "Reglas:\n"
        "- Determina si el texto muestra evidencia razonable de que la persona "
        "realizó o está realizando el hábito indicado.\n"
        "- Sé flexible pero honesto. Si el texto no tiene relación, marca como inválido.\n"
        "- Responde ÚNICAMENTE con el JSON, sin texto adicional."
    )

    try:
        client = OpenAI(api_key=api_key, timeout=20.0)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.2,
        )
    except openai.AuthenticationError as exc:
        current_app.logger.exception("Habit text validation auth error.")
        raise ValidationUnavailableError(
            "La llave de OpenAI es inválida o ha sido revocada.",
            VALIDATION_AUTH_ERROR_CODE,
        ) from exc
    except openai.RateLimitError as exc:
        current_app.logger.exception("Habit text validation rate limit or quota exceeded.")
        raise ValidationUnavailableError(
            "Se han agotado los créditos o la cuota de OpenAI.",
            VALIDATION_QUOTA_EXCEEDED_CODE,
        ) from exc
    except Exception as exc:
        current_app.logger.exception("Habit text validation provider call failed.")
        raise ValidationUnavailableError(
            "La validación de texto no está disponible temporalmente.",
            VALIDATION_PROVIDER_UNAVAILABLE_CODE,
        ) from exc

    return _parse_ai_json_response(response.choices[0].message.content)


def analyze_habit_difficulty(
    habit_name: str,
    *,
    current_difficulty: str,
    context: dict,
) -> dict:
    """Ask OpenAI for advisory habit difficulty metadata.

    Returns:
        dict with keys: level (facil|media|dificil), explanation (str), confidence (float).
    """
    if not is_openai_configured(current_app.config):
        raise ValidationUnavailableError(
            "La recomendación de dificultad no está disponible en este entorno.",
            VALIDATION_NOT_CONFIGURED_CODE,
        )

    api_key = str(current_app.config.get("OPENAI_API_KEY") or "").strip()
    prompt = (
        "Eres un sistema que recomienda dificultad de hábitos según la Pirámide de Maslow.\n\n"
        "Niveles de Maslow y dificultad base:\n"
        "- Fisiológico (sueño, alimentación, hidratación, ejercicio básico): base 'facil'\n"
        "- Seguridad (ahorro, salud preventiva, rutinas de protección): base 'media'\n"
        "- Pertenencia (social, familia, trabajo en equipo): base 'facil' a 'media'\n"
        "- Estima (logro personal, aprendizaje, reconocimiento): base 'media' a 'dificil'\n"
        "- Autorrealización (creatividad, misión personal, crecimiento espiritual): base 'dificil'\n\n"
        f"Hábito: {habit_name}\n"
        f"Dificultad actual: {current_difficulty}\n"
        f"Contexto JSON: {json.dumps(context, ensure_ascii=False, sort_keys=True)}\n\n"
        "Responde SOLO en JSON válido con este formato:\n"
        "{\n"
        '  "level": "facil" | "media" | "dificil",\n'
        '  "maslow_level": "Fisiológico" | "Seguridad" | "Pertenencia" | "Estima" | "Autorrealización",\n'
        '  "explanation": "explicación breve en español mencionando el nivel de Maslow identificado",\n'
        '  "confidence": número entre 0 y 1\n'
        "}\n\n"
        "Reglas:\n"
        "- Identifica el nivel de Maslow del hábito y úsalo como base para la dificultad.\n"
        "- Ajusta la dificultad según el contexto recibido (racha, tasa de éxito, historial).\n"
        "- No recomiendes XP ni recompensas.\n"
        "- La recomendación es consultiva y no debe controlar premios."
    )

    try:
        client = OpenAI(api_key=api_key, timeout=10.0)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
            max_tokens=180,
            temperature=0.2,
        )
    except openai.AuthenticationError as exc:
        current_app.logger.exception("Habit difficulty auth error.")
        raise ValidationUnavailableError(
            "La llave de OpenAI es inválida o ha sido revocada.",
            VALIDATION_AUTH_ERROR_CODE,
        ) from exc
    except openai.RateLimitError as exc:
        current_app.logger.exception("Habit difficulty rate limit or quota exceeded.")
        raise ValidationUnavailableError(
            "Se han agotado los créditos o la cuota de OpenAI.",
            VALIDATION_QUOTA_EXCEEDED_CODE,
        ) from exc
    except Exception as exc:
        current_app.logger.exception("Habit difficulty provider call failed.")
        raise ValidationUnavailableError(
            "La recomendación de dificultad no está disponible temporalmente.",
            VALIDATION_PROVIDER_UNAVAILABLE_CODE,
        ) from exc

    raw = response.choices[0].message.content
    if isinstance(raw, list):
        content = "".join(
            chunk.get("text", "")
            for chunk in raw
            if isinstance(chunk, dict) and chunk.get("type") == "text"
        ).strip()
    else:
        content = str(raw or "").strip()

    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(line for line in lines if not line.strip().startswith("```"))

    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        current_app.logger.warning("Habit difficulty provider returned invalid JSON.")
        raise ValidationUnavailableError(
            "La recomendación de dificultad no está disponible temporalmente.",
            VALIDATION_PROVIDER_UNAVAILABLE_CODE,
        ) from exc

    return {
        "level": str(result.get("level", current_difficulty)),
        "maslow_level": str(result.get("maslow_level", "")),
        "explanation": str(result.get("explanation", "Sin explicación proporcionada.")),
        "confidence": float(result.get("confidence", 0.0)),
    }


def generate_motivational_message(context: dict) -> str:
    """Generate an empathetic motivational message using OpenAI.

    Args:
        context: dict with streak, today_completed, today_total, completion_rate, validations_today.

    Returns:
        Motivational message string in Spanish.

    Raises:
        ValidationUnavailableError: if OpenAI is not configured or the call fails.
    """
    if not is_openai_configured(current_app.config):
        raise ValidationUnavailableError(
            "Motivación generativa no disponible.",
            VALIDATION_NOT_CONFIGURED_CODE,
        )

    api_key = str(current_app.config.get("OPENAI_API_KEY") or "").strip()
    streak = context.get("streak", 0)
    today_completed = context.get("today_completed", 0)
    today_total = context.get("today_total", 0)
    completion_rate = context.get("completion_rate", 0)

    prompt = (
        "Eres un coach de hábitos empático y motivador. "
        "Genera un mensaje motivacional breve (máximo 2 oraciones) en español "
        "basado en el progreso del usuario. Sé específico, empático y alentador.\n\n"
        f"Progreso:\n"
        f"- Racha actual: {streak} días\n"
        f"- Hábitos completados hoy: {today_completed}/{today_total}\n"
        f"- Tasa de éxito general: {completion_rate}%\n\n"
        "Responde ÚNICAMENTE con el mensaje motivacional, sin comillas ni formato adicional."
    )

    try:
        client = OpenAI(api_key=api_key, timeout=8.0)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.7,
        )
    except openai.AuthenticationError as exc:
        current_app.logger.exception("Motivational message auth error.")
        raise ValidationUnavailableError(
            "La llave de OpenAI es inválida o ha sido revocada.",
            VALIDATION_AUTH_ERROR_CODE,
        ) from exc
    except openai.RateLimitError as exc:
        current_app.logger.exception("Motivational message rate limit exceeded.")
        raise ValidationUnavailableError(
            "Se han agotado los créditos o la cuota de OpenAI.",
            VALIDATION_QUOTA_EXCEEDED_CODE,
        ) from exc
    except Exception as exc:
        current_app.logger.exception("Motivational message generation failed.")
        raise ValidationUnavailableError(
            "Motivación generativa no disponible temporalmente.",
            VALIDATION_PROVIDER_UNAVAILABLE_CODE,
        ) from exc

    content = response.choices[0].message.content
    return str(content or "").strip()
