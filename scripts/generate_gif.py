"""
Shoptegrity GIF Generator
Generates animated social/marketing GIFs highlighting corporate transparency,
disguised ownership, and ethical swaps.
"""

import os
import math
import argparse
from PIL import Image, ImageDraw, ImageFont

# Colors (Shoptegrity brand palette)
NAVY = (15, 23, 42)          # #0f172a
NAVY_LIGHT = (30, 41, 59)    # #1e293b
CARD_BG = (255, 255, 255)
TEXT_DARK = (15, 23, 42)
MUTED = (100, 116, 139)      # #64748b
BORDER = (226, 232, 240)     # #e2e8f0

EMERALD = (5, 150, 105)      # #059669
EMERALD_BG = (236, 253, 245) # #ecfdf5
EMERALD_DARK = (4, 120, 87)

DANGER = (220, 38, 38)       # #dc2626
DANGER_BG = (254, 242, 242)  # #fef2f2

WARNING = (217, 119, 6)      # #d97706
WARNING_BG = (255, 251, 235)

WHITE = (255, 255, 255)

def get_font(size, bold=False):
    font_file = r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"
    if not os.path.exists(font_file):
        font_file = r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"
    try:
        return ImageFont.truetype(font_file, size)
    except Exception:
        return ImageFont.load_default()

def draw_rounded_rect(draw, bbox, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)

def ease_out_cubic(x):
    return 1 - math.pow(1 - x, 3)

def ease_in_out(x):
    return x * x * (3 - 2 * x)

def draw_top_pill(draw, text, x_center, y, fg, bg_outline, font):
    f_badge = get_font(12, bold=True)
    box = draw.textbbox((0, 0), text, font=f_badge)
    tw = box[2] - box[0]
    pw, ph = tw + 32, 24
    px1, py1 = x_center - pw // 2, y
    px2, py2 = px1 + pw, py1 + ph
    draw_rounded_rect(draw, (px1, py1, px2, py2), 12, fill=NAVY_LIGHT, outline=bg_outline, width=1)
    # small colored dot
    draw.ellipse((px1 + 10, py1 + 8, px1 + 18, py1 + 16), fill=bg_outline)
    draw.text((px1 + 24, py1 + 4), text, fill=fg, font=f_badge)

def render_frame_scanner(frame_idx, total_frames, W, H):
    """
    Renders a frame for 'The Illusion of Choice' Brand Scanner
    """
    img = Image.new("RGB", (W, H), color=NAVY)
    draw = ImageDraw.Draw(img)

    f_title = get_font(25, bold=True)
    f_sub = get_font(14, bold=False)
    f_badge = get_font(11, bold=True)
    f_card_title = get_font(18, bold=True)
    f_card_sub = get_font(13, bold=False)
    f_card_stat = get_font(13, bold=False)
    f_card_stat_bold = get_font(13, bold=True)
    f_score = get_font(28, bold=True)
    f_footer = get_font(14, bold=True)

    # Header
    draw_top_pill(draw, "SHOPTEGRITY BRAND SCANNER", W // 2, 14, EMERALD, EMERALD, f_badge)
    draw.text((W // 2, 48), "Who are you actually paying?", fill=WHITE, font=f_title, anchor="mt")
    draw.text((W // 2, 78), "Exposing conglomerate ownership behind 'natural' brands", fill=MUTED, font=f_sub, anchor="mt")

    card_y1 = 108
    card_y2 = 372
    card1_y1 = card_y1
    card1_y2 = card_y2
    card2_y1 = card_y1
    card2_y2 = card_y2
    card_w = 330
    card1_x1 = 34
    card1_x2 = card1_x1 + card_w

    card2_x1 = W - 34 - card_w
    card2_x2 = card2_x1 + card_w

    is_revealed = frame_idx >= 22

    # Card 1: Burt's Bees
    card1_border = DANGER if is_revealed else BORDER
    draw_rounded_rect(draw, (card1_x1, card1_y1, card1_x2, card1_y2), 12, fill=WHITE, outline=card1_border, width=2)

    if not is_revealed:
        # Pre-reveal state
        draw_rounded_rect(draw, (card1_x1 + 16, card1_y1 + 14, card1_x1 + 140, card1_y1 + 34), 6, fill=EMERALD_BG)
        draw.text((card1_x1 + 24, card1_y1 + 17), "ECO & NATURAL", fill=EMERALD, font=f_badge)
        
        draw.text((card1_x1 + 16, card1_y1 + 44), "Burt's Bees", fill=TEXT_DARK, font=f_card_title)
        draw.text((card1_x1 + 16, card1_y1 + 68), "Lip Balm & Personal Care", fill=MUTED, font=f_card_sub)

        draw_rounded_rect(draw, (card1_x1 + 16, card1_y1 + 100, card1_x2 - 16, card1_y1 + 170), 8, fill=WARNING_BG, outline=WARNING, width=1)
        draw.text((card1_x1 + 26, card1_y1 + 114), "100% Natural Origin", fill=(180, 83, 9), font=f_card_stat_bold)
        draw.text((card1_x1 + 26, card1_y1 + 138), "Eco-friendly apothecary branding", fill=MUTED, font=f_card_stat)

        draw.text((card1_x1 + 16, card1_y1 + 195), "Store Shelf Perception:", fill=MUTED, font=f_card_stat)
        draw.text((card1_x1 + 16, card1_y1 + 218), "Small independent business", fill=TEXT_DARK, font=f_card_stat_bold)
        draw.text((card1_x1 + 16, card1_y1 + 240), "Ethical, feel-good purchase", fill=MUTED, font=f_card_stat)
    else:
        # Corporate reveal state
        draw_rounded_rect(draw, (card1_x1 + 16, card1_y1 + 14, card1_x1 + 210, card1_y1 + 34), 6, fill=DANGER_BG)
        draw.text((card1_x1 + 24, card1_y1 + 17), "ALERT: 100% SUBSIDIARY OF", fill=DANGER, font=f_badge)

        draw.text((card1_x1 + 16, card1_y1 + 44), "CLOROX CO.", fill=DANGER, font=f_card_title)
        draw.text((card1_x1 + 16, card1_y1 + 68), "NYSE: CLX | Acquired for $925M", fill=MUTED, font=f_card_sub)

        draw_rounded_rect(draw, (card1_x1 + 16, card1_y1 + 96, card1_x2 - 16, card1_y1 + 152), 8, fill=DANGER_BG)
        draw.text((card1_x1 + 26, card1_y1 + 104), "Integrity Score", fill=DANGER, font=f_card_stat)
        draw.text((card1_x2 - 26, card1_y1 + 124), "28 / 100", fill=DANGER, font=f_score, anchor="rm")

        draw.text((card1_x1 + 16, card1_y1 + 168), "- CEO-to-Worker Pay:", fill=MUTED, font=f_card_stat)
        draw.text((card1_x1 + 175, card1_y1 + 168), "295 to 1", fill=DANGER, font=f_card_stat_bold)

        draw.text((card1_x1 + 16, card1_y1 + 192), "- Capital Extraction:", fill=MUTED, font=f_card_stat)
        draw.text((card1_x1 + 175, card1_y1 + 192), "$1.2B Buybacks", fill=DANGER, font=f_card_stat_bold)

        draw.text((card1_x1 + 16, card1_y1 + 216), "- Community Wealth:", fill=MUTED, font=f_card_stat)
        draw.text((card1_x1 + 175, card1_y1 + 216), "Severe Wealth Leak", fill=DANGER, font=f_card_stat_bold)

        draw.text((card1_x1 + 16, card1_y1 + 240), "- Evidence Sources:", fill=MUTED, font=f_card_stat)
        draw.text((card1_x1 + 175, card1_y1 + 240), "SEC 10-K & ECHO", fill=MUTED, font=f_card_stat_bold)

    # Scanner Beam
    if 16 <= frame_idx <= 30:
        scan_progress = (frame_idx - 16) / 14
        beam_y = int(card_y1 + scan_progress * (card_y2 - card_y1))
        draw.line([(card1_x1 - 6, beam_y), (card1_x2 + 6, beam_y)], fill=(239, 68, 68), width=3)
        draw.line([(card1_x1, beam_y - 2), (card1_x2, beam_y - 2)], fill=(254, 202, 202), width=1)
        draw.line([(card1_x1, beam_y + 2), (card1_x2, beam_y + 2)], fill=(254, 202, 202), width=1)

    # Middle Arrow
    if frame_idx >= 34:
        mid_x = W // 2
        mid_y = (card_y1 + card_y2) // 2
        draw.ellipse((mid_x - 18, mid_y - 18, mid_x + 18, mid_y + 18), fill=EMERALD, outline=WHITE, width=2)
        draw.text((mid_x, mid_y - 1), "->", fill=WHITE, font=f_badge, anchor="mm")
        draw.text((mid_x, mid_y - 28), "SWAP TO", fill=EMERALD, font=f_badge, anchor="mm")

    # Card 2: Dr. Bronner's
    if frame_idx >= 36:
        slide_in = min(1.0, (frame_idx - 36) / 12)
        offset_y = int((1.0 - ease_out_cubic(slide_in)) * 30)
        c2_y1 = card_y1 + offset_y
        c2_y2 = card_y2 + offset_y

        draw_rounded_rect(draw, (card2_x1, c2_y1, card2_x2, c2_y2), 12, fill=WHITE, outline=EMERALD, width=2)
        draw_rounded_rect(draw, (card2_x1 + 16, c2_y1 + 14, card2_x1 + 170, c2_y1 + 34), 6, fill=EMERALD_BG)
        draw.text((card2_x1 + 24, c2_y1 + 17), "[VERIFIED MISSION]", fill=EMERALD, font=f_badge)

        draw.text((card2_x1 + 16, c2_y1 + 44), "Dr. Bronner's", fill=TEXT_DARK, font=f_card_title)
        draw.text((card2_x1 + 16, c2_y1 + 68), "Family-Owned / Certified B-Corp", fill=MUTED, font=f_card_sub)

        draw_rounded_rect(draw, (card2_x1 + 16, c2_y1 + 96, card2_x2 - 16, c2_y1 + 152), 8, fill=EMERALD_BG)
        draw.text((card2_x1 + 26, c2_y1 + 104), "Integrity Score", fill=EMERALD_DARK, font=f_card_stat)
        draw.text((card2_x2 - 26, c2_y1 + 124), "96 / 100", fill=EMERALD, font=f_score, anchor="rm")

        draw.text((card2_x1 + 16, c2_y1 + 168), "- Executive Pay Cap:", fill=MUTED, font=f_card_stat)
        draw.text((card2_x1 + 175, c2_y1 + 168), "5 to 1 Cap", fill=EMERALD_DARK, font=f_card_stat_bold)

        draw.text((card2_x1 + 16, c2_y1 + 192), "- Stock Buybacks:", fill=MUTED, font=f_card_stat)
        draw.text((card2_x1 + 175, c2_y1 + 192), "$0 (Zero Wall St)", fill=EMERALD_DARK, font=f_card_stat_bold)

        draw.text((card2_x1 + 16, c2_y1 + 216), "- Profits to Mission:", fill=MUTED, font=f_card_stat)
        draw.text((card2_x1 + 175, c2_y1 + 216), "1/3 to Staff/Charity", fill=EMERALD_DARK, font=f_card_stat_bold)

        draw.text((card2_x1 + 16, c2_y1 + 240), "- Supply Chain:", fill=MUTED, font=f_card_stat)
        draw.text((card2_x1 + 175, c2_y1 + 240), "Regenerative Organic", fill=EMERALD_DARK, font=f_card_stat_bold)

    # Footer
    footer_y = H - 28
    draw.line([(0, footer_y - 12), (W, footer_y - 12)], fill=NAVY_LIGHT, width=1)
    pulse = (math.sin(frame_idx / 4) + 1) / 2 if frame_idx > 50 else 0
    cta_color = (int(5 + pulse * 35), int(150 + pulse * 50), int(105 + pulse * 40))
    draw.text((W // 2, footer_y), "Search 500+ brands & ethical swaps at Shoptegrity.com ->", fill=cta_color, font=f_footer, anchor="mm")

    return img

def render_frame_pe_rollup(frame_idx, total_frames, W, H):
    """
    Renders a frame for 'The Trojan Horse Plumber' (PE Rollup Detector)
    """
    img = Image.new("RGB", (W, H), color=NAVY)
    draw = ImageDraw.Draw(img)

    f_title = get_font(25, bold=True)
    f_sub = get_font(14, bold=False)
    f_badge = get_font(11, bold=True)
    f_card_title = get_font(18, bold=True)
    f_card_sub = get_font(13, bold=False)
    f_card_stat = get_font(13, bold=False)
    f_card_stat_bold = get_font(13, bold=True)
    f_score = get_font(26, bold=True)
    f_footer = get_font(14, bold=True)

    # Header
    draw_top_pill(draw, "DISGUISED ROLLUP DETECTOR", W // 2, 14, WARNING, WARNING, f_badge)
    draw.text((W // 2, 48), "Did Private Equity buy your local plumber?", fill=WHITE, font=f_title, anchor="mt")
    draw.text((W // 2, 78), "Wall Street platforms keep the trusted family name while hiking rates 40%", fill=MUTED, font=f_sub, anchor="mt")

    card_y1 = 108
    card_y2 = 372
    card1_y1 = card_y1
    card1_y2 = card_y2
    card2_y1 = card_y1
    card2_y2 = card_y2
    card_w = 330
    card1_x1 = 34
    card1_x2 = card1_x1 + card_w

    card2_x1 = W - 34 - card_w
    card2_x2 = card2_x1 + card_w

    is_revealed = frame_idx >= 22

    # Card 1: Contractor
    card1_border = DANGER if is_revealed else BORDER
    draw_rounded_rect(draw, (card1_x1, card1_y1, card1_x2, card1_y2), 12, fill=WHITE, outline=card1_border, width=2)

    if not is_revealed:
        draw_rounded_rect(draw, (card1_x1 + 16, card1_y1 + 14, card1_x1 + 155, card1_y1 + 34), 6, fill=WARNING_BG)
        draw.text((card1_x1 + 24, card1_y1 + 17), "HERITAGE BRANDING", fill=WARNING, font=f_badge)

        draw.text((card1_x1 + 16, card1_y1 + 44), "Miller & Sons HVAC", fill=TEXT_DARK, font=f_card_title)
        draw.text((card1_x1 + 16, card1_y1 + 68), "\"Serving our valley since 1982\"", fill=MUTED, font=f_card_sub)

        draw_rounded_rect(draw, (card1_x1 + 16, card1_y1 + 100, card1_x2 - 16, card1_y1 + 170), 8, fill=(241, 245, 249), outline=BORDER, width=1)
        draw.text((card1_x1 + 26, card1_y1 + 114), "Trusted neighborhood service van", fill=TEXT_DARK, font=f_card_stat_bold)
        draw.text((card1_x1 + 26, card1_y1 + 138), "Familiar logo, local phone number", fill=MUTED, font=f_card_stat)

        draw.text((card1_x1 + 16, card1_y1 + 195), "Customer Perception:", fill=MUTED, font=f_card_stat)
        draw.text((card1_x1 + 16, card1_y1 + 218), "Locally owned family business", fill=TEXT_DARK, font=f_card_stat_bold)
        draw.text((card1_x1 + 16, card1_y1 + 240), "Owner lives in your neighborhood", fill=MUTED, font=f_card_stat)
    else:
        draw_rounded_rect(draw, (card1_x1 + 16, card1_y1 + 14, card1_x1 + 200, card1_y1 + 34), 6, fill=DANGER_BG)
        draw.text((card1_x1 + 24, card1_y1 + 17), "ALERT: DISGUISED PE ROLLUP", fill=DANGER, font=f_badge)

        draw.text((card1_x1 + 16, card1_y1 + 44), "Apex Services Platform", fill=DANGER, font=f_card_title)
        draw.text((card1_x1 + 16, card1_y1 + 68), "Secret Parent: $4.2B Buyout Fund", fill=MUTED, font=f_card_sub)

        draw_rounded_rect(draw, (card1_x1 + 16, card1_y1 + 96, card1_x2 - 16, card1_y1 + 152), 8, fill=DANGER_BG)
        draw.text((card1_x1 + 26, card1_y1 + 104), "Ownership Tier", fill=DANGER, font=f_card_stat)
        draw.text((card1_x2 - 26, card1_y1 + 124), "Tier 5 (PE Rollup)", fill=DANGER, font=f_score, anchor="rm")

        draw.text((card1_x1 + 16, card1_y1 + 168), "- Service Markup:", fill=MUTED, font=f_card_stat)
        draw.text((card1_x1 + 175, card1_y1 + 168), "+38% Post-Acquisition", fill=DANGER, font=f_card_stat_bold)

        draw.text((card1_x1 + 16, card1_y1 + 192), "- Technician Model:", fill=MUTED, font=f_card_stat)
        draw.text((card1_x1 + 175, card1_y1 + 192), "Sales Commission Quotas", fill=DANGER, font=f_card_stat_bold)

        draw.text((card1_x1 + 16, card1_y1 + 216), "- Community Retention:", fill=MUTED, font=f_card_stat)
        draw.text((card1_x1 + 175, card1_y1 + 216), "Under 15% Stays Local", fill=DANGER, font=f_card_stat_bold)

        draw.text((card1_x1 + 16, card1_y1 + 240), "- Evidence Source:", fill=MUTED, font=f_card_stat)
        draw.text((card1_x1 + 175, card1_y1 + 240), "Secretary of State Filings", fill=MUTED, font=f_card_stat_bold)

    # Scanner Beam
    if 16 <= frame_idx <= 30:
        scan_progress = (frame_idx - 16) / 14
        beam_y = int(card_y1 + scan_progress * (card_y2 - card_y1))
        draw.line([(card1_x1 - 6, beam_y), (card1_x2 + 6, beam_y)], fill=(239, 68, 68), width=3)
        draw.line([(card1_x1, beam_y - 2), (card1_x2, beam_y - 2)], fill=(254, 202, 202), width=1)
        draw.line([(card1_x1, beam_y + 2), (card1_x2, beam_y + 2)], fill=(254, 202, 202), width=1)

    # Middle Arrow
    if frame_idx >= 34:
        mid_x = W // 2
        mid_y = (card_y1 + card_y2) // 2
        draw.ellipse((mid_x - 18, mid_y - 18, mid_x + 18, mid_y + 18), fill=EMERALD, outline=WHITE, width=2)
        draw.text((mid_x, mid_y - 1), "->", fill=WHITE, font=f_badge, anchor="mm")
        draw.text((mid_x, mid_y - 28), "CHOOSE", fill=EMERALD, font=f_badge, anchor="mm")

    # Card 2: True Independent Co-op
    if frame_idx >= 36:
        slide_in = min(1.0, (frame_idx - 36) / 12)
        offset_y = int((1.0 - ease_out_cubic(slide_in)) * 30)
        c2_y1 = card_y1 + offset_y
        c2_y2 = card_y2 + offset_y

        draw_rounded_rect(draw, (card2_x1, c2_y1, card2_x2, c2_y2), 12, fill=WHITE, outline=EMERALD, width=2)
        draw_rounded_rect(draw, (card2_x1 + 16, c2_y1 + 14, card2_x1 + 195, c2_y1 + 34), 6, fill=EMERALD_BG)
        draw.text((card2_x1 + 24, c2_y1 + 17), "[VERIFIED INDEPENDENT]", fill=EMERALD, font=f_badge)

        draw.text((card2_x1 + 16, c2_y1 + 44), "Cascade Techs Co-op", fill=TEXT_DARK, font=f_card_title)
        draw.text((card2_x1 + 16, c2_y1 + 68), "100% Worker-Owned & Licensed", fill=MUTED, font=f_card_sub)

        draw_rounded_rect(draw, (card2_x1 + 16, c2_y1 + 96, card2_x2 - 16, c2_y1 + 152), 8, fill=EMERALD_BG)
        draw.text((card2_x1 + 26, c2_y1 + 104), "Ownership Tier", fill=EMERALD_DARK, font=f_card_stat)
        draw.text((card2_x2 - 26, c2_y1 + 124), "Tier 1 (Direct)", fill=EMERALD, font=f_score, anchor="rm")

        draw.text((card2_x1 + 16, c2_y1 + 168), "- Pricing Transparency:", fill=MUTED, font=f_card_stat)
        draw.text((card2_x1 + 175, c2_y1 + 168), "Zero Sales Quotas", fill=EMERALD_DARK, font=f_card_stat_bold)

        draw.text((card2_x1 + 16, c2_y1 + 192), "- Local Recirculation:", fill=MUTED, font=f_card_stat)
        draw.text((card2_x1 + 175, c2_y1 + 192), "68% Stays in County", fill=EMERALD_DARK, font=f_card_stat_bold)

        draw.text((card2_x1 + 16, c2_y1 + 216), "- Service Quality:", fill=MUTED, font=f_card_stat)
        draw.text((card2_x1 + 175, c2_y1 + 216), "Master Tech Onsite", fill=EMERALD_DARK, font=f_card_stat_bold)

        draw.text((card2_x1 + 16, c2_y1 + 240), "- Customer Protection:", fill=MUTED, font=f_card_stat)
        draw.text((card2_x1 + 175, c2_y1 + 240), "No Private Equity Cut", fill=EMERALD_DARK, font=f_card_stat_bold)

    # Footer
    footer_y = H - 28
    draw.line([(0, footer_y - 12), (W, footer_y - 12)], fill=NAVY_LIGHT, width=1)
    pulse = (math.sin(frame_idx / 4) + 1) / 2 if frame_idx > 50 else 0
    cta_color = (int(5 + pulse * 35), int(150 + pulse * 50), int(105 + pulse * 40))
    draw.text((W // 2, footer_y), "Look up contractors in your zip code at Shoptegrity.com/local ->", fill=cta_color, font=f_footer, anchor="mm")

    return img

def render_frame_dollar_flow(frame_idx, total_frames, W, H):
    """
    Renders a frame for 'The $100 Wealth Flow' (Megacorp Leak vs Co-op Recirculation)
    """
    img = Image.new("RGB", (W, H), color=NAVY)
    draw = ImageDraw.Draw(img)

    f_title = get_font(25, bold=True)
    f_sub = get_font(14, bold=False)
    f_badge = get_font(11, bold=True)
    f_card_title = get_font(17, bold=True)
    f_card_stat = get_font(13, bold=False)
    f_card_stat_bold = get_font(13, bold=True)
    f_score = get_font(30, bold=True)
    f_footer = get_font(14, bold=True)

    # Header
    draw_top_pill(draw, "THE $100 DOLLAR VOTE", W // 2, 14, EMERALD, EMERALD, f_badge)
    draw.text((W // 2, 48), "Where does your $100 actually travel?", fill=WHITE, font=f_title, anchor="mt")
    draw.text((W // 2, 78), "Every purchase either builds local resilience or fuels Wall Street extraction", fill=MUTED, font=f_sub, anchor="mt")

    card_y1 = 104
    card_y2 = 388
    card1_y1 = card_y1
    card1_y2 = card_y2
    card2_y1 = card_y1
    card2_y2 = card_y2
    card_w = 330
    card1_x1 = 34
    card1_x2 = card1_x1 + card_w

    card2_x1 = W - 34 - card_w
    card2_x2 = card2_x1 + card_w

    # Animation progress with pause at end
    anim_progress = min(1.0, frame_idx / (total_frames * 0.65))
    eased_p = ease_in_out(anim_progress)

    # Card 1: Megacorp
    draw_rounded_rect(draw, (card1_x1, card1_y1, card1_x2, card1_y2), 12, fill=WHITE, outline=DANGER, width=2)
    draw_rounded_rect(draw, (card1_x1 + 16, card1_y1 + 14, card1_x1 + 155, card1_y1 + 34), 6, fill=DANGER_BG)
    draw.text((card1_x1 + 24, card1_y1 + 17), "MEGACORP RETAIL", fill=DANGER, font=f_badge)
    draw.text((card1_x1 + 16, card1_y1 + 44), "$100 at Megastore / Amazon", fill=TEXT_DARK, font=f_card_title)
    
    leak_amt = int(eased_p * 82)
    draw_rounded_rect(draw, (card1_x1 + 16, card1_y1 + 74, card1_x2 - 16, card1_y1 + 130), 8, fill=DANGER_BG)
    draw.text((card1_x1 + 24, card1_y1 + 82), "Leaves Community:", fill=DANGER, font=f_card_stat)
    draw.text((card1_x2 - 24, card1_y1 + 102), f"${leak_amt}", fill=DANGER, font=f_score, anchor="rm")

    bar_y = card1_y1 + 144
    draw.rectangle([card1_x1 + 16, bar_y, card1_x2 - 16, bar_y + 12], fill=BORDER)
    draw.rectangle([card1_x1 + 16, bar_y, card1_x1 + 16 + int((card_w - 32) * (leak_amt / 100)), bar_y + 12], fill=DANGER)

    draw.text((card1_x1 + 16, card1_y1 + 170), "- Wall Street Buybacks:", fill=MUTED, font=f_card_stat)
    draw.text((card1_x1 + 195, card1_y1 + 170), "$42", fill=DANGER, font=f_card_stat_bold)

    draw.text((card1_x1 + 16, card1_y1 + 194), "- Offshore Tax Havens:", fill=MUTED, font=f_card_stat)
    draw.text((card1_x1 + 195, card1_y1 + 194), "$21", fill=DANGER, font=f_card_stat_bold)

    draw.text((card1_x1 + 16, card1_y1 + 218), "- Executive Bonuses:", fill=MUTED, font=f_card_stat)
    draw.text((card1_x1 + 195, card1_y1 + 218), "$19", fill=DANGER, font=f_card_stat_bold)

    draw.text((card1_x1 + 16, card1_y1 + 242), "- Stays in Community:", fill=MUTED, font=f_card_stat)
    draw.text((card1_x1 + 195, card1_y1 + 242), f"${100 - leak_amt} only", fill=DANGER, font=f_card_stat_bold)

    # Card 2: Local Co-op
    draw_rounded_rect(draw, (card2_x1, card2_y1, card2_x2, card2_y2), 12, fill=WHITE, outline=EMERALD, width=2)
    draw_rounded_rect(draw, (card2_x1 + 16, card2_y1 + 14, card2_x1 + 180, card2_y1 + 34), 6, fill=EMERALD_BG)
    draw.text((card2_x1 + 24, card2_y1 + 17), "LOCAL COOPERATIVE", fill=EMERALD, font=f_badge)
    draw.text((card2_x1 + 16, card2_y1 + 44), "$100 at Co-op / Direct Maker", fill=TEXT_DARK, font=f_card_title)

    retain_amt = int(eased_p * 68)
    draw_rounded_rect(draw, (card2_x1 + 16, card2_y1 + 74, card2_x2 - 16, card2_y1 + 130), 8, fill=EMERALD_BG)
    draw.text((card2_x1 + 24, card2_y1 + 82), "Recirculates Locally:", fill=EMERALD_DARK, font=f_card_stat)
    draw.text((card2_x2 - 24, card2_y1 + 102), f"${retain_amt}", fill=EMERALD, font=f_score, anchor="rm")

    draw.rectangle([card2_x1 + 16, bar_y, card2_x2 - 16, bar_y + 12], fill=BORDER)
    draw.rectangle([card2_x1 + 16, bar_y, card2_x1 + 16 + int((card_w - 32) * (retain_amt / 100)), bar_y + 12], fill=EMERALD)

    draw.text((card2_x1 + 16, card2_y1 + 170), "- Local Farmer / Grower:", fill=MUTED, font=f_card_stat)
    draw.text((card2_x1 + 195, card2_y1 + 170), "$38", fill=EMERALD_DARK, font=f_card_stat_bold)

    draw.text((card2_x1 + 16, card2_y1 + 194), "- Living Wage Payroll:", fill=MUTED, font=f_card_stat)
    draw.text((card2_x1 + 195, card2_y1 + 194), "$22", fill=EMERALD_DARK, font=f_card_stat_bold)

    draw.text((card2_x1 + 16, card2_y1 + 218), "- Local Taxes & Schools:", fill=MUTED, font=f_card_stat)
    draw.text((card2_x1 + 195, card2_y1 + 218), "$8", fill=EMERALD_DARK, font=f_card_stat_bold)

    draw.text((card2_x1 + 16, card2_y1 + 242), "- Community Retained:", fill=MUTED, font=f_card_stat)
    draw.text((card2_x1 + 195, card2_y1 + 242), f"${retain_amt}", fill=EMERALD_DARK, font=f_card_stat_bold)

    # VS icon in middle
    mid_x = W // 2
    mid_y = (card_y1 + card_y2) // 2
    draw.ellipse((mid_x - 16, mid_y - 16, mid_x + 16, mid_y + 16), fill=NAVY_LIGHT, outline=BORDER, width=1)
    draw.text((mid_x, mid_y - 1), "VS", fill=WHITE, font=f_badge, anchor="mm")

    # Footer
    footer_y = H - 28
    draw.line([(0, footer_y - 12), (W, footer_y - 12)], fill=NAVY_LIGHT, width=1)
    pulse = (math.sin(frame_idx / 4) + 1) / 2 if frame_idx > 50 else 0
    cta_color = (int(5 + pulse * 35), int(150 + pulse * 50), int(105 + pulse * 40))
    draw.text((W // 2, footer_y), "Calculate your household dollar impact at Shoptegrity.com/flows ->", fill=cta_color, font=f_footer, anchor="mm")

    return img

def generate_gif(concept="scanner", output_path=None, total_frames=80, fps=18):
    W, H = 760, 440
    frames = []

    print(f"Generating '{concept}' GIF with {total_frames} frames @ {fps} fps ({W}x{H})...")

    render_func = {
        "scanner": render_frame_scanner,
        "rollup": render_frame_pe_rollup,
        "dollar": render_frame_dollar_flow
    }.get(concept, render_frame_scanner)

    for i in range(total_frames):
        frame = render_func(i, total_frames, W, H)
        frames.append(frame)

    if not output_path:
        os.makedirs("web/static/img", exist_ok=True)
        output_path = f"web/static/img/shoptegrity_{concept}.gif"

    parent_dir = os.path.dirname(output_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    duration_ms = int(1000 / fps)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
        disposal=2
    )

    size_kb = os.path.getsize(output_path) / 1024
    print(f"GIF saved successfully to {output_path} ({size_kb:.1f} KB)")
    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Shoptegrity animated GIFs")
    parser.add_argument("--concept", choices=["scanner", "rollup", "dollar", "all"], default="scanner")
    parser.add_argument("--output", default=None)
    parser.add_argument("--frames", type=int, default=80)
    parser.add_argument("--fps", type=int, default=18)
    args = parser.parse_args()

    if args.concept == "all":
        for c in ["scanner", "rollup", "dollar"]:
            generate_gif(concept=c, total_frames=args.frames, fps=args.fps)
    else:
        generate_gif(concept=args.concept, output_path=args.output, total_frames=args.frames, fps=args.fps)
