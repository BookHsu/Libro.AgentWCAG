import { Html, Head, Main, NextScript } from "next/document";

export default function Document() {
  return (
    <Html>
      <Head />
      <body>
        <Main />
        <Image src="/hero.png" width={1200} height={800} />
        <NextScript />
      </body>
    </Html>
  );
}
