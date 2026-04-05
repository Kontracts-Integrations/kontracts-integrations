"use client";

export function Header({ title }: { title?: string }) {
  return (
    <header className="flex h-12 items-center border-b bg-card px-6">
      <h1 className="text-base font-semibold">{title}</h1>
    </header>
  );
}
