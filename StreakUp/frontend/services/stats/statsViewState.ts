interface StatsSummaryLike {
  total_habits?: number | null;
}

interface DetailedStatsLike {
  summary?: StatsSummaryLike | null;
}

export type StatsViewState =
  | { kind: "ready" }
  | { kind: "empty"; title: string; message: string }
  | { kind: "error"; title: string; message: string };

const GENERIC_ERROR_MESSAGE = "No se pudieron cargar tus estadísticas reales. Intenta de nuevo en unos momentos.";

export function getStatsViewState(
  stats: DetailedStatsLike | null,
  errorMessage?: string | null,
): StatsViewState {
  if (errorMessage) {
    return {
      kind: "error",
      title: "Estadísticas no disponibles",
      message: errorMessage.trim() || GENERIC_ERROR_MESSAGE,
    };
  }

  if (!stats) {
    return {
      kind: "error",
      title: "Estadísticas no disponibles",
      message: GENERIC_ERROR_MESSAGE,
    };
  }

  if ((stats.summary?.total_habits ?? 0) <= 0) {
    return {
      kind: "empty",
      title: "Aún no hay estadísticas",
      message: "Agrega hábitos y completa al menos uno para ver progreso real aquí.",
    };
  }

  return { kind: "ready" };
}
