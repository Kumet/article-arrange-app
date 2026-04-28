from __future__ import annotations

import html


def build_article_document_html(*, title: str, meta_description: str, body_html: str) -> str:
    safe_title = html.escape(title, quote=True)
    safe_meta_description = html.escape(meta_description, quote=True)
    return f"""<!DOCTYPE html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{safe_title}</title>
    <meta name="description" content="{safe_meta_description}" />
    <style>
      :root {{
        color-scheme: light;
      }}
      * {{
        box-sizing: border-box;
      }}
      body {{
        margin: 0;
        background:
          radial-gradient(circle at top, #f8fafc 0%, #eef2f7 42%, #e2e8f0 100%);
        color: #0f172a;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      .page {{
        padding: 32px 18px 56px;
      }}
      main {{
        max-width: 960px;
        margin: 0 auto;
        padding: 40px 24px 64px;
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 28px;
        background: rgba(255, 255, 255, 0.96);
        box-shadow: 0 28px 70px rgba(15, 23, 42, 0.08);
      }}
      .meta-description {{
        margin: 0 0 32px;
        color: #475569;
        font-size: 1rem;
        line-height: 1.9;
      }}
      h1, h2, h3 {{
        color: #0f172a;
        letter-spacing: -0.02em;
      }}
      h1 {{
        margin: 0 0 18px;
        font-size: clamp(2rem, 4vw, 2.8rem);
        line-height: 1.18;
      }}
      h2 {{
        margin: 42px 0 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid #cbd5e1;
        font-size: 1.6rem;
        line-height: 1.35;
      }}
      h3 {{
        margin: 28px 0 12px;
        padding-left: 12px;
        border-left: 4px solid #94a3b8;
        font-size: 1.2rem;
        line-height: 1.45;
      }}
      p, li {{
        line-height: 1.9;
        font-size: 1rem;
      }}
      p {{
        margin: 14px 0;
      }}
      ul, ol {{
        margin: 18px 0 22px;
        padding-left: 24px;
      }}
      strong {{
        color: #0f172a;
      }}
      a {{
        color: #1d4ed8;
      }}
      table {{
        width: 100%;
        margin: 28px 0;
        border-collapse: collapse;
        table-layout: fixed;
        overflow: hidden;
        border: 1px solid #cbd5e1;
        border-radius: 16px;
      }}
      th, td {{
        border: 1px solid #cbd5e1;
        padding: 12px;
        text-align: left;
        vertical-align: top;
      }}
      thead {{
        background: #e2e8f0;
      }}
      tbody tr:nth-child(even) {{
        background: #f8fafc;
      }}
      blockquote {{
        margin: 20px 0;
        padding: 12px 16px;
        border-left: 4px solid #cbd5e1;
        background: #f8fafc;
        color: #334155;
      }}
      code {{
        padding: 2px 6px;
        border-radius: 7px;
        background: #f1f5f9;
        font-size: 0.92em;
      }}
      pre {{
        overflow-x: auto;
        margin: 20px 0;
        padding: 16px;
        border-radius: 16px;
        background: #0f172a;
        color: #f8fafc;
      }}
      pre code {{
        padding: 0;
        background: transparent;
        color: inherit;
      }}
      @media (min-width: 768px) {{
        .page {{
          padding: 40px 28px 72px;
        }}
        main {{
          padding: 52px 44px 76px;
        }}
      }}
    </style>
  </head>
  <body>
    <div class="page">
      <main>
        <h1>{safe_title}</h1>
        <p class="meta-description">{safe_meta_description}</p>
        {body_html}
      </main>
    </div>
  </body>
</html>
"""
