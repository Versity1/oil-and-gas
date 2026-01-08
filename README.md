# Techo Drill Innovation - Website Project

A modern, responsive website template designed for an Oil & Gas company, featuring a comprehensive suite of pages for services, portfolio management, investment tracking, and user dashboards.

## Project Overview

This project implements a professional, corporate website with a focus on mobile responsiveness and clean UI/UX. It utilizes a grid-based layout for desktop and an optimized mobile experience with offcanvas navigation.

### Key Features
-   **Responsive Design**: Fully adaptable layout that works seamlessly on mobile, tablet, and desktop devices.
-   **Modern UI**: Built with Tailwind CSS logic (configured via CDN) for rapid styling and consistency.
-   **Interactive Navigation**:
    -   **Desktop**: Sticky header with full navigation links and dashboard CTA.
    -   **Mobile**: Offcanvas slide-out menu and a bottom navigation bar for quick access to core features.
-   **Dashboard System**: Integrated dashboard templates for user account management, trading, and investment monitoring.

## Technology Stack
-   **HTML5**: Semantic markup.
-   **CSS**: Tailwind CSS (via CDN) for utility-first styling.
-   **JavaScript**: Vanilla JS for navigation toggles and interactivity.
-   **Icons**: Material Symbols Outlined (Google Fonts).
-   **Fonts**: Space Grotesk (Headings) and Noto Sans (Body).

## File Structure

```
oil-and-gas/
├── templates/
│   ├── home.html              # Main landing page with Hero, Services, Partners, FAQ
│   ├── about.html             # Company information, leadership, and timeline
│   ├── services.html          # Detailed services listing
│   ├── products.html          # Portfolio/Project case studies
│   ├── contact.html           # Contact form and location info
│   ├── dashboard.html         # User dashboard main view
│   ├── investment-plan.html   # Investment options and market view
│   ├── shares.html            # Trading interface
│   ├── transaction-history.html # User transaction logs
│   └── login.html             # Authentication page
├── static/                    # (Optional) Directory for local assets
├── README.md                  # Project documentation
└── .gitignore                # Git configuration
```

## Setup & Usage

Since this project uses a CDN for Tailwind CSS, you can simply open any `.html` file directly in your web browser.

1.  Clone or download the repository.
2.  Navigate to the `templates/` folder.
3.  Open `home.html` in your browser to view the landing page.

## Recent Updates
-   **Home Page**: Expanded with "Why Choose Us", "Partners", "Latest Insights", and "FAQ" sections.
-   **Navigation**: 
    -   Standardized header and offcanvas menu across all pages.
    -   Removed mobile bottom navigation from front-facing pages (`home`, `about`, `services`, `contact`) to declutter the view.
    -   Retained bottom navigation on app-like pages (`dashboard`, `products`, `market`).
