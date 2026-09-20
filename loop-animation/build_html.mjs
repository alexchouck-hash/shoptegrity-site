import fs from 'fs';
import path from 'path';

const gsapCode = fs.readFileSync('node_modules/gsap/dist/gsap.min.js', 'utf8');

const htmlContent = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=760, height=440, initial-scale=1.0">
  <title>The Loop - Shoptegrity</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
    }
    body {
      background-color: #020617;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      overflow: hidden;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    #stage-container {
      width: 760px;
      height: 440px;
      position: relative;
      background-color: #0f172a;
      overflow: hidden;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
    }
    svg {
      width: 760px;
      height: 440px;
      display: block;
      position: absolute;
      top: 0;
      left: 0;
    }
    /* Typography & overlay */
    .headline {
      position: absolute;
      top: 50px;
      left: 20px;
      right: 20px;
      text-align: center;
      color: #ffffff;
      font-size: 20.5px;
      font-weight: 700;
      letter-spacing: -0.2px;
      line-height: 1.25;
      text-shadow: 0 2px 8px rgba(0,0,0,0.8);
      pointer-events: none;
      transition: opacity 0.2s;
    }
    .caption {
      position: absolute;
      top: 78px;
      left: 20px;
      right: 20px;
      text-align: center;
      color: #94a3b8;
      font-size: 12.5px;
      font-style: italic;
      font-weight: 500;
      line-height: 1.3;
      pointer-events: none;
      opacity: 0;
    }
    .pill-header {
      position: absolute;
      top: 14px;
      left: 50%;
      transform: translateX(-50%);
      height: 24px;
      background: #1e293b;
      border: 1px solid #10b981;
      border-radius: 12px;
      display: flex;
      align-items: center;
      padding: 0 14px;
      gap: 7px;
      pointer-events: none;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    }
    .pill-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background-color: #10b981;
      box-shadow: 0 0 6px #10b981;
    }
    .pill-text {
      color: #10b981;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
    }
    .footer-bar {
      position: absolute;
      bottom: 0;
      left: 0;
      width: 760px;
      height: 28px;
      border-top: 1px solid #1e293b;
      display: flex;
      align-items: center;
      justify-content: center;
      pointer-events: none;
      background: rgba(15, 23, 42, 0.85);
    }
    .footer-text {
      color: #10b981;
      font-size: 12.5px;
      font-weight: 600;
      letter-spacing: 0.5px;
    }
  </style>
</head>
<body>
  <div id="stage-container">
    <!-- Header Pill -->
    <div class="pill-header">
      <div class="pill-dot"></div>
      <div class="pill-text">THE LOOP</div>
    </div>

    <!-- On-screen Headlines & Captions -->
    <div id="headline-el" class="headline">Every dollar you spend goes somewhere.</div>
    <div id="caption-el" class="caption">Top 10% of households own ~90% of stocks (Federal Reserve)</div>

    <!-- Main Scene SVG -->
    <svg id="scene" viewBox="0 0 760 440">
      <defs>
        <!-- Glow filters -->
        <filter id="gold-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="green-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="red-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        <!-- Coin Gradient -->
        <radialGradient id="coinGrad" cx="35%" cy="35%" r="65%">
          <stop offset="0%" stop-color="#fef08a" />
          <stop offset="40%" stop-color="#fbbf24" />
          <stop offset="90%" stop-color="#d97706" />
          <stop offset="100%" stop-color="#b45309" />
        </radialGradient>

        <linearGradient id="towerGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#475569" />
          <stop offset="60%" stop-color="#334155" />
          <stop offset="100%" stop-color="#1e293b" />
        </linearGradient>

        <linearGradient id="parentBadgeGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="#ef4444" />
          <stop offset="100%" stop-color="#b91c1c" />
        </linearGradient>

        <!-- Awning Stripes -->
        <pattern id="storeAwning" width="12" height="12" patternUnits="userSpaceOnUse">
          <rect width="6" height="12" fill="#f97316" />
          <rect x="6" width="6" height="12" fill="#ffedd5" />
        </pattern>
        <pattern id="farmAwning" width="10" height="10" patternUnits="userSpaceOnUse">
          <rect width="5" height="10" fill="#10b981" />
          <rect x="5" width="5" height="10" fill="#ecfdf5" />
        </pattern>
        <pattern id="cafeAwning" width="10" height="10" patternUnits="userSpaceOnUse">
          <rect width="5" height="10" fill="#8b5cf6" />
          <rect x="5" width="5" height="10" fill="#f5f3ff" />
        </pattern>
      </defs>

      <!-- Background Network / Neighborhood Roads -->
      <g id="roads" opacity="0.45">
        <!-- Community Ring Road -->
        <path d="M 180 300 Q 150 200 230 170 Q 320 140 430 150 Q 560 170 580 230 Q 600 320 530 340 Q 370 380 180 300 Z"
              fill="none" stroke="#334155" stroke-width="26" stroke-linecap="round" stroke-linejoin="round" />
        <path d="M 180 300 Q 150 200 230 170 Q 320 140 430 150 Q 560 170 580 230 Q 600 320 530 340 Q 370 380 180 300 Z"
              fill="none" stroke="#475569" stroke-width="1.5" stroke-dasharray="6,6" />
        
        <!-- Drainage Highway to Parent Co. & Out of town -->
        <path d="M 580 210 L 580 120 L 730 65"
              fill="none" stroke="#334155" stroke-width="20" stroke-linecap="round" stroke-linejoin="round" />
      </g>

      <!-- Drain Highway Red Trail & Arrow (Shot 3 & 4) -->
      <g id="drain-trail-group">
        <path id="drain-trail" d="M 180 300 C 280 280 460 250 580 230 L 580 125 L 740 60"
              fill="none" stroke="#ef4444" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"
              filter="url(#red-glow)" stroke-dasharray="800" stroke-dashoffset="800" opacity="0" />
        <!-- Red exit arrow head -->
        <g id="drain-arrow-head" opacity="0" transform="translate(735, 62) rotate(-23)">
          <polygon points="0,0 -16,-8 -12,0 -16,8" fill="#ef4444" filter="url(#red-glow)" />
        </g>
      </g>

      <!-- Green Neighbor Trail (Shot 7) -->
      <g id="neighbor-trail-group">
        <path id="green-trail"
              d="M 180 300 C 170 230 190 190 230 170 C 310 140 370 145 430 150 C 390 200 360 270 340 335 C 440 370 500 360 530 335 C 460 320 280 340 180 300"
              fill="none" stroke="#10b981" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"
              filter="url(#green-glow)" stroke-dasharray="1200" stroke-dashoffset="1200" opacity="0" />
      </g>

      <!-- Surrounding Town Residential Houses -->
      <g id="residential-houses">
        <!-- House Northwest (120, 210) -->
        <g id="house-nw" class="town-building" transform="translate(100, 190)">
          <rect x="0" y="14" width="34" height="26" rx="3" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
          <polygon points="17,0 -3,15 37,15" fill="#334155"/>
          <rect id="win-nw" class="house-win" x="10" y="22" width="14" height="10" rx="2" fill="#fef08a" opacity="0.85"/>
        </g>

        <!-- House North (305, 115) -->
        <g id="house-n" class="town-building" transform="translate(305, 115)">
          <rect x="0" y="14" width="32" height="24" rx="3" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
          <polygon points="16,0 -2,15 34,15" fill="#334155"/>
          <rect id="win-n" class="house-win" x="10" y="21" width="12" height="10" rx="2" fill="#fef08a" opacity="0.85"/>
        </g>

        <!-- House East (650, 260) -->
        <g id="house-e" class="town-building" transform="translate(635, 245)">
          <rect x="0" y="14" width="36" height="28" rx="3" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
          <polygon points="18,0 -3,15 39,15" fill="#334155"/>
          <rect id="win-e" class="house-win" x="11" y="23" width="14" height="11" rx="2" fill="#fef08a" opacity="0.85"/>
        </g>

        <!-- House Southwest (125, 340) -->
        <g id="house-sw" class="town-building" transform="translate(110, 325)">
          <rect x="0" y="14" width="32" height="24" rx="3" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
          <polygon points="16,0 -2,15 34,15" fill="#334155"/>
          <rect id="win-sw" class="house-win" x="9" y="21" width="14" height="10" rx="2" fill="#fef08a" opacity="0.85"/>
        </g>
      </g>

      <!-- Key Community Node: 1. Neighbor Farmer (230, 170) -->
      <g id="node-farmer" class="town-building" transform="translate(200, 140)">
        <rect x="0" y="20" width="56" height="38" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
        <!-- Barn roof -->
        <polygon points="28,2 -4,21 60,21" fill="#065f46" stroke="#047857" stroke-width="1"/>
        <!-- Farm Awning -->
        <rect x="6" y="22" width="44" height="10" rx="2" fill="url(#farmAwning)"/>
        <!-- Farm window / stand -->
        <rect id="win-farmer" class="house-win" x="12" y="36" width="32" height="15" rx="2" fill="#fef08a" opacity="0.85"/>
        <text x="28" y="47" text-anchor="middle" font-size="8" font-weight="700" fill="#1e293b">PRODUCE</text>
        <!-- Node label pill -->
        <rect x="3" y="60" width="50" height="14" rx="7" fill="#064e3b" stroke="#10b981" stroke-width="1"/>
        <text x="28" y="70.5" text-anchor="middle" font-size="8" font-weight="700" fill="#a7f3d0">Farmer</text>
      </g>

      <!-- Key Community Node: 2. Neighbor Mechanic / Plumber (430, 150) -->
      <g id="node-mechanic" class="town-building" transform="translate(405, 120)">
        <rect x="0" y="16" width="58" height="42" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
        <!-- Roof -->
        <polygon points="29,0 -3,17 61,17" fill="#1e3a5f" stroke="#2563eb" stroke-width="1"/>
        <!-- Garage roll door / lit window -->
        <rect id="win-mechanic" class="house-win" x="10" y="27" width="38" height="24" rx="2" fill="#fef08a" opacity="0.85"/>
        <!-- Garage slats -->
        <line x1="10" y1="33" x2="48" y2="33" stroke="#d97706" stroke-width="1"/>
        <line x1="10" y1="39" x2="48" y2="39" stroke="#d97706" stroke-width="1"/>
        <line x1="10" y1="45" x2="48" y2="45" stroke="#d97706" stroke-width="1"/>
        <!-- Wrench icon -->
        <circle cx="29" cy="22" r="4" fill="#38bdf8"/>
        <!-- Label pill -->
        <rect x="2" y="62" width="54" height="14" rx="7" fill="#1e3a5f" stroke="#38bdf8" stroke-width="1"/>
        <text x="29" y="72.5" text-anchor="middle" font-size="8" font-weight="700" fill="#bae6fd">Mechanic</text>
      </g>

      <!-- Key Community Node: 3. Credit Union / Bank (340, 335) -->
      <g id="node-creditunion" class="town-building" transform="translate(310, 305)">
        <rect x="0" y="18" width="62" height="42" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
        <!-- Pediment Triangle -->
        <polygon points="31,2 -2,19 64,19" fill="#0f766e" stroke="#14b8a6" stroke-width="1"/>
        <!-- Classical pillars -->
        <rect x="8" y="22" width="6" height="26" fill="#e2e8f0"/>
        <rect x="20" y="22" width="6" height="26" fill="#e2e8f0"/>
        <rect x="36" y="22" width="6" height="26" fill="#e2e8f0"/>
        <rect x="48" y="22" width="6" height="26" fill="#e2e8f0"/>
        <!-- Interior Lit Window behind pillars -->
        <rect id="win-creditunion" class="house-win" x="14" y="25" width="34" height="20" rx="2" fill="#fef08a" opacity="0.85"/>
        <!-- Label pill -->
        <rect x="0" y="63" width="62" height="14" rx="7" fill="#134e4a" stroke="#2dd4bf" stroke-width="1"/>
        <text x="31" y="73.5" text-anchor="middle" font-size="7.5" font-weight="700" fill="#99f6e4">Credit Union</text>
      </g>

      <!-- Key Community Node: 4. Local Cafe / Bakery (530, 335) -->
      <g id="node-cafe" class="town-building" transform="translate(505, 305)">
        <rect x="0" y="18" width="56" height="40" rx="4" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
        <polygon points="28,2 -3,19 59,19" fill="#581c87" stroke="#7e22ce" stroke-width="1"/>
        <!-- Awning -->
        <rect x="5" y="19" width="46" height="9" rx="2" fill="url(#cafeAwning)"/>
        <!-- Cafe Window -->
        <rect id="win-cafe" class="house-win" x="10" y="32" width="36" height="18" rx="2" fill="#fef08a" opacity="0.85"/>
        <!-- Coffee cup glyph -->
        <path d="M 23 41 h 8 a 4 4 0 0 1 4 4 v 1 a 4 4 0 0 1 -4 4 h -8 Z" fill="#78350f"/>
        <!-- Label pill -->
        <rect x="5" y="62" width="46" height="14" rx="7" fill="#4c1d95" stroke="#a855f7" stroke-width="1"/>
        <text x="28" y="72.5" text-anchor="middle" font-size="8" font-weight="700" fill="#e9d5ff">Local Cafe</text>
      </g>

      <!-- THE STOREFRONT & PARENT CO. TOWER COMPLEX (580, 210) -->
      <g id="store-tower-complex">
        <!-- Parent Co. Gray Monolith Tower (Behind Storefront) -->
        <g id="parent-tower" transform="translate(545, 95)">
          <!-- Tower block -->
          <rect x="0" y="20" width="76" height="145" rx="3" fill="url(#towerGrad)" stroke="#64748b" stroke-width="2"/>
          <!-- Rooftop Antenna -->
          <line x1="38" y1="20" x2="38" y2="2" stroke="#94a3b8" stroke-width="2.5"/>
          <circle id="antenna-led" cx="38" cy="2" r="3.5" fill="#ef4444" filter="url(#red-glow)"/>
          
          <!-- Corporate Grid Windows -->
          <g id="tower-grid-windows" fill="#38bdf8" opacity="0.25">
            <rect x="10" y="30" width="10" height="7" rx="1"/>
            <rect x="10" y="44" width="10" height="7" rx="1"/>
            <rect x="10" y="58" width="10" height="7" rx="1"/>
            <rect x="10" y="72" width="10" height="7" rx="1"/>
            <rect x="10" y="86" width="10" height="7" rx="1"/>
            <rect x="25" y="30" width="10" height="7" rx="1"/>
            <rect x="25" y="44" width="10" height="7" rx="1"/>
            <rect x="25" y="58" width="10" height="7" rx="1"/>
            <rect x="25" y="72" width="10" height="7" rx="1"/>
            <rect x="25" y="86" width="10" height="7" rx="1"/>
            <rect x="40" y="30" width="10" height="7" rx="1"/>
            <rect x="40" y="44" width="10" height="7" rx="1"/>
            <rect x="40" y="58" width="10" height="7" rx="1"/>
            <rect x="40" y="72" width="10" height="7" rx="1"/>
            <rect x="40" y="86" width="10" height="7" rx="1"/>
            <rect x="55" y="30" width="10" height="7" rx="1"/>
            <rect x="55" y="44" width="10" height="7" rx="1"/>
            <rect x="55" y="58" width="10" height="7" rx="1"/>
            <rect x="55" y="72" width="10" height="7" rx="1"/>
            <rect x="55" y="86" width="10" height="7" rx="1"/>
          </g>

          <!-- Big Parent Co. Label Badge -->
          <rect id="parent-badge" x="4" y="32" width="68" height="20" rx="4" fill="url(#parentBadgeGrad)" stroke="#fca5a5" stroke-width="1.5" opacity="0.95"/>
          <text id="parent-text" x="38" y="46" text-anchor="middle" font-size="9" font-weight="800" fill="#ffffff" letter-spacing="0.8px">PARENT CO.</text>
        </g>

        <!-- Cozy Storefront Facade (Flips down in Shot 3, Wireframe in Shot 6) -->
        <g id="storefront-facade" transform="translate(538, 185)" style="transform-origin: 580px 255px;">
          <!-- Drop shadow when upright -->
          <rect id="facade-shadow" x="-3" y="10" width="90" height="64" rx="4" fill="#020617" opacity="0.5"/>
          
          <!-- Facade structure -->
          <rect id="facade-body" x="0" y="12" width="84" height="60" rx="4" fill="#1e293b" stroke="#f59e0b" stroke-width="2"/>
          
          <!-- Roof / Awning -->
          <polygon id="facade-roof" points="42,0 -4,15 88,15" fill="#78350f" stroke="#b45309" stroke-width="1.5"/>
          <rect id="facade-awning" x="4" y="15" width="76" height="12" rx="2" fill="url(#storeAwning)"/>
          
          <!-- Rustic Sign: "Est. 1982" with leaf icon -->
          <rect id="facade-sign" x="12" y="29" width="60" height="15" rx="3" fill="#451a03" stroke="#d97706" stroke-width="1"/>
          <!-- Leaf icon -->
          <path id="facade-leaf" d="M 18 36 C 18 33 22 32 23 36 C 23 39 19 40 18 36 Z" fill="#10b981"/>
          <text id="facade-sign-text" x="45" y="39.5" text-anchor="middle" font-size="8" font-weight="700" fill="#fef3c7" letter-spacing="0.5px">Est. 1982</text>
          
          <!-- Warm Store Windows -->
          <rect id="win-store-1" class="house-win" x="10" y="47" width="28" height="20" rx="2" fill="#fef08a" opacity="0.9"/>
          <rect id="win-store-2" class="house-win" x="46" y="47" width="28" height="20" rx="2" fill="#fef08a" opacity="0.9"/>
          <line x1="24" y1="47" x2="24" y2="67" stroke="#b45309" stroke-width="1"/>
          <line x1="60" y1="47" x2="60" y2="67" stroke="#b45309" stroke-width="1"/>
          
          <!-- Planter Box -->
          <rect id="facade-planter" x="8" y="68" width="68" height="4" rx="2" fill="#15803d"/>
        </g>
      </g>

      <!-- KEY NODE: "YOU" HOUSE & CLOCK (180, 300) -->
      <g id="node-you" transform="translate(145, 260)">
        <!-- Clock hovering over You (Shot 1-7) -->
        <g id="you-clock" transform="translate(35, -25)">
          <circle cx="0" cy="0" r="14" fill="#0f172a" stroke="#38bdf8" stroke-width="2"/>
          <circle cx="0" cy="0" r="2" fill="#ffffff"/>
          <!-- Clock Hour Hand -->
          <line id="clock-hour" x1="0" y1="0" x2="0" y2="-6" stroke="#ffffff" stroke-width="2" stroke-linecap="round"/>
          <!-- Clock Minute Hand -->
          <line id="clock-min" x1="0" y1="0" x2="0" y2="-9" stroke="#38bdf8" stroke-width="1.5" stroke-linecap="round"/>
        </g>

        <!-- Main House Structure -->
        <rect x="4" y="20" width="62" height="44" rx="4" fill="#1e293b" stroke="#3b82f6" stroke-width="2.5"/>
        <!-- Peaked Roof -->
        <polygon points="35,0 -4,22 74,22" fill="#1d4ed8" stroke="#60a5fa" stroke-width="1.5"/>
        <!-- Chimney -->
        <rect x="50" y="4" width="8" height="12" fill="#334155"/>
        
        <!-- Lit Windows & Door -->
        <rect id="win-you-1" class="house-win" x="12" y="28" width="18" height="16" rx="2" fill="#fef08a" opacity="0.95"/>
        <line x1="21" y1="28" x2="21" y2="44" stroke="#d97706" stroke-width="1"/>
        <line x1="12" y1="36" x2="30" y2="36" stroke="#d97706" stroke-width="1"/>
        
        <rect id="win-you-2" class="house-win" x="40" y="28" width="18" height="16" rx="2" fill="#fef08a" opacity="0.95"/>
        <line x1="49" y1="28" x2="49" y2="44" stroke="#d97706" stroke-width="1"/>
        <line x1="40" y1="36" x2="58" y2="36" stroke="#d97706" stroke-width="1"/>
        
        <rect x="27" y="47" width="16" height="17" rx="1" fill="#1e3a5f" stroke="#60a5fa" stroke-width="1"/>

        <!-- Prominent "YOU" Badge -->
        <rect x="10" y="68" width="50" height="18" rx="9" fill="#2563eb" stroke="#93c5fd" stroke-width="1.5"/>
        <text x="35" y="81" text-anchor="middle" font-size="10" font-weight="800" fill="#ffffff" letter-spacing="1px">YOU</text>
      </g>

      <!-- AD / PHONE / BILLBOARD ICON (Center 390, 230) -->
      <g id="ad-billboard" transform="translate(390, 230)">
        <!-- Pulsing wave rings -->
        <circle id="ad-pulse-1" cx="0" cy="0" r="18" fill="none" stroke="#f59e0b" stroke-width="2" opacity="0"/>
        <circle id="ad-pulse-2" cx="0" cy="0" r="28" fill="none" stroke="#ef4444" stroke-width="1.5" opacity="0"/>

        <!-- Phone / Screen Stand -->
        <rect x="-3" y="16" width="6" height="14" fill="#475569"/>
        <rect x="-10" y="28" width="20" height="4" rx="2" fill="#334155"/>

        <!-- Phone device -->
        <rect x="-16" y="-22" width="32" height="40" rx="5" fill="#0f172a" stroke="#cbd5e1" stroke-width="2"/>
        <rect x="-13" y="-18" width="26" height="30" rx="2" fill="#1e293b"/>
        <!-- Ad Banner graphic -->
        <rect id="ad-banner-bg" x="-11" y="-15" width="22" height="14" rx="2" fill="#ef4444"/>
        <text x="0" y="-6" text-anchor="middle" font-size="6.5" font-weight="900" fill="#ffffff">SALE!</text>
        <rect x="-10" y="2" width="20" height="2" fill="#94a3b8"/>
        <rect x="-8" y="6" width="16" height="2" fill="#f59e0b"/>
      </g>

      <!-- SEARCH BAR (Shot 6) (380, 95) -->
      <g id="search-bar" opacity="0" transform="translate(260, 90)">
        <!-- Search box container -->
        <rect x="0" y="0" width="240" height="32" rx="16" fill="#1e293b" stroke="#38bdf8" stroke-width="1.8"
              filter="url(#gold-glow)"/>
        <!-- Magnifying Glass Icon -->
        <g transform="translate(14, 9)">
          <circle cx="5" cy="5" r="4.5" fill="none" stroke="#38bdf8" stroke-width="1.8"/>
          <line x1="8.5" y1="8.5" x2="13" y2="13" stroke="#38bdf8" stroke-width="1.8" stroke-linecap="round"/>
        </g>
        <!-- Typed Query Text -->
        <text id="search-text" x="38" y="20" font-size="13" font-weight="600" fill="#f8fafc" font-family="monospace"></text>
        <!-- Blinking cursor -->
        <line id="search-cursor" x1="38" y1="9" x2="38" y2="23" stroke="#38bdf8" stroke-width="2"/>
      </g>

      <!-- VIEWER'S HAND (Shot 8) (Center Bottom 380, 385) -->
      <g id="viewer-hand" opacity="0" transform="translate(380, 385)">
        <!-- Golden / Emerald Radiance rings -->
        <circle id="hand-glow-ring" cx="0" cy="0" r="28" fill="none" stroke="#10b981" stroke-width="1.5" opacity="0.6"/>
        <circle cx="0" cy="0" r="38" fill="none" stroke="#10b981" stroke-width="1" stroke-dasharray="4,4" opacity="0.3"/>
        
        <!-- Elegant Cupped Hand Vector Outline -->
        <path d="M -30 18 C -22 10 -15 8 -2 8 C 12 8 20 10 28 18 C 22 24 10 26 -2 26 C -14 26 -24 24 -30 18 Z"
              fill="#064e3b" stroke="#10b981" stroke-width="2"/>
        <path d="M -24 12 C -18 3 -8 0 -2 0 C 6 0 16 3 22 12"
              fill="none" stroke="#34d399" stroke-width="2" stroke-linecap="round"/>
        <text x="0" y="22" text-anchor="middle" font-size="8.5" font-weight="700" fill="#a7f3d0" letter-spacing="0.5px">YOUR BALLOT</text>
      </g>

      <!-- THE GLOWING GOLD COIN -->
      <g id="coin-token" transform="translate(180, 150)" filter="url(#gold-glow)">
        <!-- Outer Glow Ring -->
        <circle cx="0" cy="0" r="16" fill="none" stroke="#fef08a" stroke-width="1.5" opacity="0.7"/>
        <!-- Main Coin Body -->
        <circle cx="0" cy="0" r="13" fill="url(#coinGrad)" stroke="#78350f" stroke-width="1.2"/>
        <!-- Inner Stamped Ring -->
        <circle cx="0" cy="0" r="10" fill="none" stroke="#fbbf24" stroke-width="1" stroke-dasharray="2,1.5"/>
        <!-- Dollar Sign -->
        <text x="0" y="4.5" text-anchor="middle" font-size="12" font-weight="900" fill="#ffffff"
              style="text-shadow: 0 1px 2px #78350f;">$</text>
      </g>

      <!-- Cross-fade veil for 100% seamless loop -->
      <rect id="loop-veil" x="0" y="0" width="760" height="440" fill="#0f172a" opacity="0" pointer-events="none"/>
    </svg>

    <!-- Footer Bar -->
    <div class="footer-bar">
      <span class="footer-text">Shoptegrity.com</span>
    </div>
  </div>

  <!-- GSAP Library Inlined -->
  <script>
\${gsapCode}
  </script>

  <!-- Master Animation Timeline -->
  <script>
    const headlineEl = document.getElementById('headline-el');
    const captionEl = document.getElementById('caption-el');
    const coin = document.getElementById('coin-token');
    const facade = document.getElementById('storefront-facade');
    const facadeBody = document.getElementById('facade-body');
    const facadeShadow = document.getElementById('facade-shadow');
    const drainTrail = document.getElementById('drain-trail');
    const drainArrow = document.getElementById('drain-arrow-head');
    const greenTrail = document.getElementById('green-trail');
    const adPulse1 = document.getElementById('ad-pulse-1');
    const adPulse2 = document.getElementById('ad-pulse-2');
    const clockMin = document.getElementById('clock-min');
    const clockHour = document.getElementById('clock-hour');
    const searchBar = document.getElementById('search-bar');
    const searchText = document.getElementById('search-text');
    const searchCursor = document.getElementById('search-cursor');
    const viewerHand = document.getElementById('viewer-hand');
    const loopVeil = document.getElementById('loop-veil');
    
    // Windows to control
    const allWindows = document.querySelectorAll('.house-win');
    const winNW = document.getElementById('win-nw');
    const winN = document.getElementById('win-n');
    const winE = document.getElementById('win-e');
    const winSW = document.getElementById('win-sw');
    const winFarmer = document.getElementById('win-farmer');
    const winMechanic = document.getElementById('win-mechanic');
    const winCreditUnion = document.getElementById('win-creditunion');
    const winCafe = document.getElementById('win-cafe');
    const winYou1 = document.getElementById('win-you-1');
    const winYou2 = document.getElementById('win-you-2');
    const winStore1 = document.getElementById('win-store-1');
    const winStore2 = document.getElementById('win-store-2');

    // Create Master Timeline
    const tl = gsap.timeline({ paused: true });

    // Initialize default states at t=0
    tl.set(coin, { x: 180, y: 140, scale: 1, opacity: 1 }, 0);
    tl.set(headlineEl, { textContent: "Every dollar you spend goes somewhere.", opacity: 1 }, 0);
    tl.set(captionEl, { opacity: 0 }, 0);
    tl.set(facade, { rotationX: 0, y: 0, scaleY: 1, opacity: 1 }, 0);
    tl.set(facadeBody, { stroke: "#f59e0b", strokeDasharray: "none", fill: "#1e293b" }, 0);
    tl.set(drainTrail, { strokeDashoffset: 800, opacity: 0 }, 0);
    tl.set(drainArrow, { opacity: 0 }, 0);
    tl.set(greenTrail, { strokeDashoffset: 1200, opacity: 0 }, 0);
    tl.set(adPulse1, { opacity: 0, scale: 1 }, 0);
    tl.set(adPulse2, { opacity: 0, scale: 1 }, 0);
    tl.set(clockMin, { rotation: 0, transformOrigin: "0 0" }, 0);
    tl.set(clockHour, { rotation: 0, transformOrigin: "0 0" }, 0);
    tl.set(searchBar, { opacity: 0, y: 0 }, 0);
    tl.set(searchText, { textContent: "" }, 0);
    tl.set(viewerHand, { opacity: 0, scale: 0.9 }, 0);
    tl.set(allWindows, { fill: "#fef08a", opacity: 0.85 }, 0);
    tl.set(loopVeil, { opacity: 0 }, 0);

    // =========================================================================
    // SHOT 1: 0.0 to 2.5s
    // "Every dollar you spend goes somewhere."
    // A simple top-down neighborhood: 8 to 10 small house/shop icons in a ring,
    // warm lit windows. A coin drops into one house marked "You."
    // =========================================================================
    tl.to(coin, {
      y: 300,
      duration: 1.2,
      ease: "bounce.out"
    }, 0.3);

    // Normal slow clock ticking at "You"
    tl.to(clockMin, {
      rotation: 180,
      duration: 2.5,
      ease: "none"
    }, 0);

    // =========================================================================
    // SHOT 2: 2.5 to 5.5s
    // "You think it goes here."
    // A phone/billboard icon pulses. The coin slides from You to a cozy storefront
    // with a rustic sign ("Est. 1982", leaf logo).
    // =========================================================================
    tl.to(headlineEl, {
      opacity: 0,
      duration: 0.2,
      onComplete: () => { headlineEl.textContent = "You think it goes here."; }
    }, 2.3);
    tl.to(headlineEl, { opacity: 1, duration: 0.3 }, 2.5);

    // Phone / Ad billboard pulses
    tl.to(adPulse1, { opacity: 0.8, scale: 1.6, duration: 0.8, repeat: 2, yoyo: false, ease: "power1.out" }, 2.5);
    tl.to(adPulse2, { opacity: 0.6, scale: 1.8, duration: 0.8, repeat: 2, yoyo: false, ease: "power1.out" }, 2.7);

    // Coin moves along path from "You" (180, 300) to cozy storefront (580, 235)
    tl.to(coin, {
      x: 360,
      y: 260,
      duration: 1.3,
      ease: "power1.inOut"
    }, 2.8);
    tl.to(coin, {
      x: 580,
      y: 235,
      duration: 1.2,
      ease: "power1.out"
    }, 4.1);

    tl.to(clockMin, {
      rotation: 360,
      duration: 3.0,
      ease: "none"
    }, 2.5);

    // =========================================================================
    // SHOT 3: 5.5 to 8.5s
    // "It goes here."
    // small: Top 10% of households own ~90% of stocks (Federal Reserve)
    // The storefront front flips forward like a stage flat. Behind it: a plain
    // gray tower labeled "Parent Co." The coin passes straight through the facade,
    // up the tower, and exits the frame on a red arrow.
    // =========================================================================
    tl.to(headlineEl, {
      opacity: 0,
      duration: 0.2,
      onComplete: () => { headlineEl.textContent = "It goes here."; }
    }, 5.3);
    tl.to(headlineEl, { opacity: 1, duration: 0.3 }, 5.5);

    // Fed citation caption fades in
    tl.to(captionEl, { opacity: 1, duration: 0.4 }, 5.8);

    // Storefront facade falls flat like a movie set prop!
    tl.to(facade, {
      y: 35,
      scaleY: 0.15,
      opacity: 0.75,
      duration: 0.7,
      ease: "power2.in"
    }, 5.7);

    // Red drain trail activates
    tl.set(drainTrail, { opacity: 1 }, 6.2);
    tl.to(drainTrail, {
      strokeDashoffset: 0,
      duration: 1.8,
      ease: "power2.in"
    }, 6.2);
    tl.to(drainArrow, { opacity: 1, duration: 0.3 }, 7.5);

    // Coin passes straight through fallen facade, shoots up the Parent Co tower,
    // and exits off frame along red arrow
    tl.to(coin, {
      x: 580,
      y: 130,
      duration: 1.0,
      ease: "power1.in"
    }, 6.4);
    tl.to(coin, {
      x: 770,
      y: 50,
      duration: 0.8,
      scale: 0.7,
      opacity: 0,
      ease: "power2.in"
    }, 7.4);

    // =========================================================================
    // SHOT 4: 8.5 to 12.0s
    // Fast repeat, 3 laps in 3 seconds: coin in, coin out. With each lap two
    // house windows go dark. A small clock over "You" spins faster.
    // An ad icon pulses again.
    // Text: "Less money here. Longer hours. Less time to choose." (8.5 - 10.2s)
    // then: "So you buy what the ad says. Again." (10.2 - 12.0s)
    // =========================================================================
    tl.to(captionEl, { opacity: 0, duration: 0.3 }, 8.4);
    tl.to(headlineEl, {
      opacity: 0,
      duration: 0.15,
      onComplete: () => { headlineEl.textContent = "Less money here. Longer hours. Less time to choose."; }
    }, 8.4);
    tl.to(headlineEl, { opacity: 1, duration: 0.25 }, 8.55);

    // Clock over You spins rapidly!
    tl.to(clockMin, {
      rotation: 2160,
      duration: 3.5,
      ease: "power2.in"
    }, 8.5);

    // Ad pulses rapidly
    tl.to(adPulse1, { opacity: 0.9, scale: 2.0, duration: 0.45, repeat: 6, ease: "power1.out" }, 8.6);
    tl.to(adPulse2, { opacity: 0.8, scale: 2.2, duration: 0.45, repeat: 6, ease: "power1.out" }, 8.8);

    // Drain Lap 1 (8.6 to 9.6s)
    tl.set(coin, { x: 180, y: 140, scale: 0.8, opacity: 0 }, 8.6);
    tl.to(coin, { y: 300, opacity: 1, duration: 0.25, ease: "power1.in" }, 8.65);
    tl.to(coin, { x: 580, y: 235, duration: 0.4, ease: "power1.inOut" }, 8.9);
    tl.to(coin, { x: 770, y: 50, opacity: 0, duration: 0.35, ease: "power2.in" }, 9.3);
    // 2 windows dim
    tl.to([winNW, winSW], { fill: "#1e293b", opacity: 0.2, duration: 0.3 }, 9.3);

    // Drain Lap 2 (9.7 to 10.7s)
    tl.set(coin, { x: 180, y: 140, scale: 0.8, opacity: 0 }, 9.7);
    tl.to(coin, { y: 300, opacity: 1, duration: 0.25, ease: "power1.in" }, 9.75);
    tl.to(coin, { x: 580, y: 235, duration: 0.4, ease: "power1.inOut" }, 10.0);
    tl.to(coin, { x: 770, y: 50, opacity: 0, duration: 0.35, ease: "power2.in" }, 10.4);
    // 2 more windows dim
    tl.to([winN, winE], { fill: "#1e293b", opacity: 0.2, duration: 0.3 }, 10.4);

    // Text swap at 10.2s: "So you buy what the ad says. Again."
    tl.to(headlineEl, {
      opacity: 0,
      duration: 0.15,
      onComplete: () => { headlineEl.textContent = "So you buy what the ad says. Again."; }
    }, 10.15);
    tl.to(headlineEl, { opacity: 1, duration: 0.25 }, 10.3);

    // Drain Lap 3 (10.8 to 11.8s)
    tl.set(coin, { x: 180, y: 140, scale: 0.8, opacity: 0 }, 10.8);
    tl.to(coin, { y: 300, opacity: 1, duration: 0.25, ease: "power1.in" }, 10.85);
    tl.to(coin, { x: 580, y: 235, duration: 0.4, ease: "power1.inOut" }, 11.1);
    tl.to(coin, { x: 770, y: 50, opacity: 0, duration: 0.35, ease: "power2.in" }, 11.5);
    // More windows dim, town is now cold and exhausted
    tl.to([winFarmer, winMechanic, winCafe, winCreditUnion, winYou2], { fill: "#1e293b", opacity: 0.2, duration: 0.4 }, 11.4);

    // Drain trail fades out
    tl.to([drainTrail, drainArrow], { opacity: 0, duration: 0.4 }, 11.8);

    // =========================================================================
    // SHOT 5: 12.0 to 13.5s
    // Freeze. Everything dims except the coin, hovering over You. Beat of stillness.
    // "Same dollar. Different direction."
    // =========================================================================
    tl.to(headlineEl, {
      opacity: 0,
      duration: 0.2,
      onComplete: () => { headlineEl.textContent = "Same dollar. Different direction."; }
    }, 11.9);
    tl.to(headlineEl, { opacity: 1, duration: 0.3 }, 12.1);

    // Restore facade upright for the next shot
    tl.set(facade, { y: 0, scaleY: 1, opacity: 1 }, 12.0);

    // Coin hovers in spotlight over "You" (180, 260), stillness
    tl.set(coin, { x: 180, y: 260, scale: 1.25, opacity: 1 }, 12.0);
    tl.to(coin, { y: 252, duration: 0.75, yoyo: true, repeat: 1, ease: "sine.inOut" }, 12.0);

    // =========================================================================
    // SHOT 6: 13.5 to 17.5s
    // A search bar types "who owns..." and the facade turns transparent, showing the tower.
    // The coin turns instead toward a neighbor's shop (farmer, plumber, co-op).
    // Window lights up.
    // "See who's really behind the counter."
    // =========================================================================
    tl.to(headlineEl, {
      opacity: 0,
      duration: 0.2,
      onComplete: () => { headlineEl.textContent = "See who's really behind the counter."; }
    }, 13.3);
    tl.to(headlineEl, { opacity: 1, duration: 0.3 }, 13.5);

    // Search bar emerges
    tl.to(searchBar, { opacity: 1, y: 10, duration: 0.4, ease: "power2.out" }, 13.6);

    // Typewriter effect for "who owns..."
    const queryStr = "who owns...";
    for (let c = 1; c <= queryStr.length; c++) {
      const sub = queryStr.slice(0, c);
      tl.call(() => {
        searchText.textContent = sub;
        const widthEst = 38 + c * 8.2;
        searchCursor.setAttribute("x1", widthEst);
        searchCursor.setAttribute("x2", widthEst);
      }, null, 14.0 + c * 0.08);
    }

    // Facade turns transparent / x-ray wireframe revealing Parent Co tower
    tl.to(facade, { opacity: 0.25, duration: 0.6 }, 14.8);
    tl.to(facadeBody, { stroke: "#38bdf8", strokeDasharray: "4,4", fill: "transparent", duration: 0.6 }, 14.8);

    // Coin turns away from facade toward Neighbor Farmer (230, 170)
    tl.to(coin, {
      x: 180,
      y: 220,
      scale: 1,
      duration: 0.6,
      ease: "power1.out"
    }, 15.3);

    tl.to(coin, {
      x: 230,
      y: 170,
      duration: 1.0,
      ease: "power2.inOut"
    }, 15.9);

    // Farmer's window lights up brightly!
    tl.to(winFarmer, { fill: "#fef08a", opacity: 1, duration: 0.4 }, 16.9);

    // =========================================================================
    // SHOT 7: 17.5 to 21.5s
    // The coin keeps moving, green trail: farmer → mechanic → credit union → cafe → back to You.
    // Each stop lights up. After one lap the whole ring glows and the clock over You slows.
    // "Your neighbor gets paid. Then spends it next door. Then it comes back to you."
    // =========================================================================
    tl.to(headlineEl, {
      opacity: 0,
      duration: 0.2,
      onComplete: () => {
        headlineEl.textContent = "Your neighbor gets paid. Then spends it next door. Then it comes back to you.";
      }
    }, 17.3);
    tl.to(headlineEl, { opacity: 1, duration: 0.3 }, 17.5);

    // Fade search bar away
    tl.to(searchBar, { opacity: 0, duration: 0.4 }, 17.5);

    // Green neighbor trail comes alive
    tl.set(greenTrail, { opacity: 1 }, 17.5);
    tl.to(greenTrail, { strokeDashoffset: 0, duration: 3.3, ease: "none" }, 17.5);

    // Stop 1: Farmer -> Mechanic (430, 150)
    tl.to(coin, {
      x: 430,
      y: 150,
      duration: 0.8,
      ease: "power1.inOut"
    }, 17.5);
    tl.to(winMechanic, { fill: "#fef08a", opacity: 1, duration: 0.3 }, 18.3);

    // Stop 2: Mechanic -> Credit Union (340, 335)
    tl.to(coin, {
      x: 340,
      y: 335,
      duration: 0.9,
      ease: "power1.inOut"
    }, 18.3);
    tl.to(winCreditUnion, { fill: "#fef08a", opacity: 1, duration: 0.3 }, 19.2);

    // Stop 3: Credit Union -> Cafe (530, 335)
    tl.to(coin, {
      x: 530,
      y: 335,
      duration: 0.8,
      ease: "power1.inOut"
    }, 19.2);
    tl.to(winCafe, { fill: "#fef08a", opacity: 1, duration: 0.3 }, 20.0);

    // Stop 4: Cafe -> Back to "You" (180, 300)
    tl.to(coin, {
      x: 180,
      y: 300,
      duration: 0.8,
      ease: "power1.out"
    }, 20.0);
    tl.to([winYou1, winYou2], { fill: "#fef08a", opacity: 1, duration: 0.3 }, 20.7);

    // Whole neighborhood glows brightly!
    tl.to(allWindows, {
      fill: "#fef08a",
      opacity: 1,
      duration: 0.6
    }, 20.6);

    // Clock over You slows to a calm gentle tick
    tl.to(clockMin, {
      rotation: "+=120",
      duration: 3.5,
      ease: "power1.out"
    }, 18.0);

    // =========================================================================
    // SHOT 8: 21.5 to 24.0s
    // Coin lands in the viewer's "hand" (bottom center). Footer bar like the other gifs.
    // "Your dollar is a vote. See the ballot."
    // Footer: Shoptegrity.com
    // Seamless loop transition: matches frame 0 at t=24.0s!
    // =========================================================================
    tl.to(headlineEl, {
      opacity: 0,
      duration: 0.2,
      onComplete: () => {
        headlineEl.textContent = "Your dollar is a vote. See the ballot.";
      }
    }, 21.3);
    tl.to(headlineEl, { opacity: 1, duration: 0.3 }, 21.5);

    // Viewer's hand appears at bottom center (380, 385)
    tl.to(viewerHand, { opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.4)" }, 21.5);

    // Green trail gently recedes
    tl.to(greenTrail, { opacity: 0, duration: 0.6 }, 21.5);

    // Coin moves from "You" down into the viewer's hand
    tl.to(coin, {
      x: 380,
      y: 385,
      scale: 1.15,
      duration: 0.8,
      ease: "power2.out"
    }, 21.6);

    // Receptive golden pulse in hand
    tl.to(coin, {
      scale: 1.0,
      duration: 0.4,
      ease: "power1.inOut"
    }, 22.4);

    // Seamless loop transition (23.3 to 24.0s)
    // Frame 480 (at t=24.0s) must visually match Frame 1 (at t=0.0s).
    // Fade out viewer's hand
    tl.to(viewerHand, { opacity: 0, duration: 0.5 }, 23.3);

    // Restore facade to original state
    tl.to(facade, { opacity: 1, duration: 0.5 }, 23.3);
    tl.to(facadeBody, { stroke: "#f59e0b", strokeDasharray: "none", fill: "#1e293b", duration: 0.5 }, 23.3);

    // Coin glides smoothly back up to starting drop position (180, 140)
    tl.to(coin, {
      x: 180,
      y: 140,
      scale: 1,
      duration: 0.6,
      ease: "power2.inOut"
    }, 23.35);

    // Headline cross-fades back to initial text for seamless loop
    tl.to(headlineEl, {
      opacity: 0,
      duration: 0.25,
      onComplete: () => {
        headlineEl.textContent = "Every dollar you spend goes somewhere.";
      }
    }, 23.65);
    tl.to(headlineEl, { opacity: 1, duration: 0.1 }, 23.9);

    // Expose required globals
    window.DURATION = 24;
    window.seek = (t) => {
      tl.time(t, false);
    };

    // If play=1 in URL, auto-loop preview
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('play') === '1') {
      tl.repeat(-1).play();
    }
  </script>
</body>
</html>`;

fs.writeFileSync('loop.html', htmlContent, 'utf8');
console.log('loop.html generated successfully, size:', fs.statSync('loop.html').size);
