"use client";

import { useState } from "react";

export function Mascot() {
  const [isBlinking, setIsBlinking] = useState(false);

  const handleInteraction = () => {
    setIsBlinking(true);
    setTimeout(() => {
      setIsBlinking(false);
    }, 220);
  };

  return (
    <div
      className="w-[285px] h-[285px] mx-auto mt-[18px] mb-[16px] relative cursor-pointer grid place-items-center animate-[mascotFloat_2.8s_ease-in-out_infinite] isolation-isolate"
      onClick={handleInteraction}
      title="Cambiar ropa de la mascota"
    >
      <div className="absolute w-[178px] h-[178px] rounded-full bg-[radial-gradient(circle,rgba(255,224,70,0.58),rgba(255,139,24,0.26)_42%,transparent_70%)] blur-[16px] -z-10 animate-[mascotGlow_2.4s_ease-in-out_infinite]" />
      
      {/* We use standard img for now since we don't know if the image is in public or optimized domain, but Image from next is better if it is local */}
      <img
        src={isBlinking ? "/mascota-streak-up-blink.png" : "/mascota-streak-up.png"}
        alt="Mascota Streak Up"
        className="w-full h-full object-contain relative z-10 drop-shadow-[0_24px_26px_rgba(0,0,0,0.34)] drop-shadow-[0_0_24px_rgba(255,166,25,0.52)] select-none pointer-events-none"
      />
    </div>
  );
}
