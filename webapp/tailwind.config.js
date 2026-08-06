/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Pastel iOS palette — one cheerful accent + muted per-status tints
        accent: {
          DEFAULT: "#FF8FB1", // cheerful pink (cute/googooli)
          soft: "#FFE3EC",
          deep: "#F26B9A",
        },
        bg: {
          DEFAULT: "#FBF7F4", // warm off-white (never pure #fff)
          soft: "#F6EFEA",
          dark: "#1F1B24", // soft dark (never pure #000)
        },
        card: {
          DEFAULT: "#FFFFFF",
          soft: "#FFF9FB",
        },
        status: {
          pending: "#F5B971", // soft amber
          confirmed: "#8EC5F2", // soft blue
          done: "#A8D8B9", // sage green
          broken: "#E8A2A2", // dusty rose
          disputed: "#C9A7E8", // soft lavender
          expired: "#B9B9C4", // muted grey
        },
        ink: {
          DEFAULT: "#3D3440", // warm dark text
          soft: "#8A7F8C",
          faint: "#BCB3BE",
        },
      },
      borderRadius: {
        card: "24px",
        sheet: "28px",
      },
      boxShadow: {
        card: "0 8px 24px rgba(0,0,0,0.06)",
        float: "0 10px 30px rgba(242,107,154,0.35)",
      },
      fontFamily: {
        vazir: ["Vazirmatn", "Tahoma", "sans-serif"],
      },
    },
  },
  plugins: [],
};
