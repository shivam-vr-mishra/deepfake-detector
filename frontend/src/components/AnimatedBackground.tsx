"use client";

export default function AnimatedBackground({
  variant = "default",
}: {
  variant?: "default" | "auth";
}) {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-brand-50 via-white to-rose-50" />
      <div className="absolute inset-0 bg-grid bg-grid-fade opacity-60" />

      <div
        className="absolute -top-40 -left-40 h-[28rem] w-[28rem] rounded-full bg-brand-300/40 blur-3xl animate-blob"
        style={{ animationDelay: "0s" }}
      />
      <div
        className="absolute top-1/3 -right-40 h-[26rem] w-[26rem] rounded-full bg-fuchsia-300/40 blur-3xl animate-blob"
        style={{ animationDelay: "3s" }}
      />
      <div
        className="absolute -bottom-40 left-1/3 h-[26rem] w-[26rem] rounded-full bg-accent-300/40 blur-3xl animate-blob"
        style={{ animationDelay: "6s" }}
      />

      {variant === "auth" && (
        <div className="absolute inset-0 bg-gradient-to-t from-white/60 via-transparent to-white/30" />
      )}
    </div>
  );
}
