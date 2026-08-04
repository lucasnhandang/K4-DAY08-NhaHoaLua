---
name: E-Commerce Support RAG
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#c7c4d7'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#908fa0'
  outline-variant: '#464554'
  surface-tint: '#c0c1ff'
  primary: '#c0c1ff'
  on-primary: '#1000a9'
  primary-container: '#8083ff'
  on-primary-container: '#0d0096'
  inverse-primary: '#494bd6'
  secondary: '#d0bcff'
  on-secondary: '#3c0091'
  secondary-container: '#571bc1'
  on-secondary-container: '#c4abff'
  tertiary: '#4edea3'
  on-tertiary: '#003824'
  tertiary-container: '#00885d'
  on-tertiary-container: '#000703'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e1e0ff'
  primary-fixed-dim: '#c0c1ff'
  on-primary-fixed: '#07006c'
  on-primary-fixed-variant: '#2f2ebe'
  secondary-fixed: '#e9ddff'
  secondary-fixed-dim: '#d0bcff'
  on-secondary-fixed: '#23005c'
  on-secondary-fixed-variant: '#5516be'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  sidebar_width: 280px
  chat_max_width: 800px
  gutter: 24px
  margin_mobile: 16px
  container_gap: 12px
  stack_spacing: 20px
---

## Brand & Style

The design system is engineered for a high-fidelity, professional AI support environment. The personality is authoritative yet helpful—positioning the RAG (Retrieval-Augmented Generation) engine as a precise tool rather than a generic chatbot.

The visual style blends **Corporate Modern** efficiency with **Glassmorphism** accents. It utilizes deep charcoal surfaces to reduce eye strain, punctuated by a vibrant tech-blue primary color to denote intelligence and action. Visual depth is achieved through translucent layers and subtle backdrop blurs, creating a "software-as-a-service" aesthetic that feels both premium and technically advanced. High-quality typography and generous whitespace ensure the information-heavy nature of support logs remains legible and approachable.

## Colors

This design system uses a **Dark Mode** foundation to emphasize high-contrast content and vibrant accents.

- **Primary & Secondary:** A gradient bridge between Indigo (#6366f1) and Violet (#8b5cf6) is used for active states, AI-generated icons, and primary call-to-actions.
- **Surface Strategy:** The background is a deep Slate (#0f172a). Elevated elements like message bubbles and the sidebar use a slightly lighter Slate (#1e293b) with an 8% white border to define edges without excessive contrast.
- **Accents:** Emerald (#10b981) is reserved for "System Online" or "Source Verified" indicators, providing a clear semantic signal of accuracy.
- **Glassmorphism:** Overlays and floating inputs utilize a 60% opacity fill of the surface color combined with a 12px backdrop-blur to maintain context of the underlying chat history.

## Typography

The typography system relies on **Inter** for its exceptional legibility in digital interfaces. 

- **Hierarchy:** Headlines use tighter letter spacing and heavier weights to anchor the page.
- **Chat Bubbles:** The primary chat text uses `body-md`. For long-form RAG responses, `body-lg` may be used to improve reading stamina.
- **Technical Content:** Since this is an e-commerce support tool, code snippets, SKU numbers, or policy IDs should use a monospaced font like **JetBrains Mono** at the `code-sm` level to distinguish them from natural language.
- **Labels:** Small caps or medium weights are used for the sidebar navigation and setting headers to maintain a disciplined, organized feel.

## Layout & Spacing

The layout follows a **structured split-view** model optimized for productivity.

1.  **Sidebar (Fixed):** A 280px left-hand column houses the "E-commerce Support RAG" branding, quick-action suggestions, and technical settings (e.g., chunk retrieval sliders).
2.  **Main Chat Area (Fluid):** The central workspace is fluid but constrained to a `chat_max_width` of 800px for optimal line length and readability.
3.  **Floating Input:** The message input is decoupled from the bottom of the screen, floating with a 24px margin from the bottom and sides, reinforcing the glassmorphic, layered aesthetic.
4.  **Responsive Reflow:** On mobile, the sidebar collapses into a hamburger menu. The chat container expands to fill 100% of the viewport width with 16px horizontal margins.

## Elevation & Depth

Visual hierarchy is established through a combination of **Tonal Layers** and **Ambient Shadows**.

- **Level 0 (Base):** The #0f172a background—the deepest layer.
- **Level 1 (Sidebar/Messages):** Surfaces use #1e293b. AI responses are slightly differentiated with a very subtle primary-tinted glow (2% Indigo).
- **Level 2 (Floating Input/Modals):** Elements that sit "above" the stream utilize glassmorphism (translucency + blur) and a soft, extra-diffused shadow: `0 10px 25px -5px rgba(0, 0, 0, 0.4)`.
- **Level 3 (Tooltips/Popovers):** Highest elevation, using a solid border and a sharper shadow to ensure they pop against the blurred layers below.

## Shapes

The design system uses a **Rounded** (16px/1rem) language to soften the "technical" feel and make the support experience more approachable.

- **Standard Elements:** Buttons, cards, and input fields use a base 8px (`rounded-md`).
- **Chat Bubbles:** Use a 16px (`rounded-lg`) radius. The corner closest to the sender's side may be sharpened (4px) to indicate directionality.
- **Floating Bar:** The main chat input uses a 24px or fully pill-shaped (`rounded-xl` to `rounded-full`) radius to emphasize its role as the primary interaction point.

## Components

- **Buttons:** Primary buttons use a solid #6366f1 fill with white text. Secondary buttons use a "ghost" style—transparent fill with a 1px border and Indigo text.
- **Chips (Suggestions):** These should be styled as low-profile interactive elements. Use a light slate background with no border, becoming primary-colored on hover to encourage clicks.
- **Input Fields:** The floating chat bar should feature a "Send" icon (Right Arrow or Paper Plane) inside the container. Use a subtle inner-shadow to create a slight "inset" look, contrasting with the overall "extruded" design.
- **Cards (Search Results):** RAG source citations should appear as mini-cards within the chat flow, featuring a small icon representing the source type (e.g., PDF, URL, Database).
- **Checkboxes & Sliders:** Use the primary Indigo color for the "active" track and handle. Sliders in the sidebar (for "Top_k" chunks) should have visible numeric labels that update in real-time.
- **AI Status Indicator:** A pulsing Indigo dot or a subtle shimmer effect on the text while the RAG engine is "thinking" or fetching data.