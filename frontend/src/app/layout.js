import "./globals.css";

export const metadata = {
  title: "Will I make it on Line 1?",
  description: "Your TTC Line 1 trip, simulated 10,000 times against real delay records.",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#f8c300",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
