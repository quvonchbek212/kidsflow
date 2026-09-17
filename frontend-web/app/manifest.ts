import type { MetadataRoute } from "next";

// Telefonda "bosh ekranga qo'shish" uchun. `display: standalone` bilan ilova
// brauzer paneli ko'rinmagan holda ochiladi.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "KIDSFLOW",
    short_name: "KIDSFLOW",
    description: "Xususiy bog'chalar uchun boshqaruv platformasi",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#edf0f5",
    theme_color: "#1668b8",
    lang: "uz",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml" },
      { src: "/apple-icon", sizes: "180x180", type: "image/png" },
    ],
  };
}
