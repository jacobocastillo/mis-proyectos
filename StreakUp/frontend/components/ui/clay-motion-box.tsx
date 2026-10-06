"use client";

import type { PropsWithChildren } from "react";
import { motion, type HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";

type ClayMotionBoxProps = PropsWithChildren<HTMLMotionProps<"div"> & {
  variant?: "primary" | "frozen" | "vibrant-blue" | "vibrant-orange" | "vibrant-purple";
  active?: boolean;
}>;

export function ClayMotionBox({
  className,
  variant = "primary",
  active = true,
  children,
  ...props
}: ClayMotionBoxProps) {
  // If not active, strip some of the 3D look to simulate 'frozen'
  const baseShadow = active ? "shadow-clay" : "shadow-none border-white/5 opacity-80 saturate-50";
  
  return (
    <motion.div
      className={cn(
        "relative rounded-3xl p-6 overflow-hidden transition-all duration-300",
        baseShadow,
        variant === "primary" && active && "bg-card border border-border",
        variant === "primary" && !active && "bg-muted text-muted-foreground",
        variant === "frozen" && "bg-muted text-muted-foreground",
        variant === "vibrant-blue" && active && "bg-clay-blue text-white border-white/10",
        variant === "vibrant-orange" && active && "bg-clay-orange text-white border-white/10",
        variant === "vibrant-purple" && active && "bg-clay-purple text-white border-white/10",
        className
      )}
      whileTap={active ? {
        scale: 0.95,
        boxShadow: "var(--shadow-clay-pressed)",
      } : {}}
      initial={active ? { y: 15, opacity: 0 } : { y: 0, opacity: 0.8 }}
      animate={active ? { y: 0, opacity: 1 } : { y: 0, opacity: 0.8 }}
      transition={{
        type: "spring",
        stiffness: 300,
        damping: 20,
      }}
      {...props}
    >
      {children}
    </motion.div>
  );
}
