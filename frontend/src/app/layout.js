import "./globals.css";

export const metadata = {
  title: "TTC Risk Simulator | What's the probability I arrive on time?",
  description:
    "Monte Carlo simulation engine for Toronto TTC subway delays. 10,000 simulated journeys from real historical data.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
