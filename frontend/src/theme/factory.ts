/**
 * Abstract Factory cho giao diện.
 *
 * Abstract factory : UIThemeFactory
 * Concrete factory : NeonDarkFactory, NeonLightFactory
 * Abstract products: Palette, Effects, ButtonSkin, CardSkin, InputSkin, BadgeSkin
 *
 * Mỗi factory sinh ra một "họ" sản phẩm khớp nhau (nút neon tối đi cùng thẻ tối, glow tối...). Component chỉ
 * phụ thuộc interface UIThemeFactory nên đổi theme = đổi factory, không component nào phải biết theme cụ thể.
 *
 * Sản phẩm là "skin" (biến CSS) chứ không phải React component: nếu factory trả về component thì đổi theme sẽ đổi
 * kiểu component → React unmount/mount lại cả cây → mất chữ đang gõ trong ô nhập, giật khung hình.
 */

export type ThemeName = "dark" | "light";
export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type CardTone = "default" | "raised" | "accent";
export type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger";

/** Một bộ biến CSS; component gắn vào style={skin} và CSS module đọc var(--...) */
export type Skin = Record<`--${string}`, string>;

export interface Palette {
  bg: string;
  frame: string;          // khung ngoài + thanh điều hướng (mẫu: nền tối bao quanh nội dung)
  surface: string;
  surface2: string;
  border: string;
  text: string;
  textMuted: string;
  accent: string;         // xanh neon
  accent2: string;        // xanh mint neon
  accent3: string;        // hồng neon — điểm nhấn hiếm
  success: string;
  warning: string;
  danger: string;
  onAccent: string;
}

export interface Effects {
  gradient: string;
  glow: string;
  glowStrong: string;
  shadow: string;
  focusRing: string;
}

export interface UIThemeFactory {
  readonly name: ThemeName;
  createPalette(): Palette;
  createEffects(): Effects;
  createButtonSkin(variant: ButtonVariant): Skin;
  createCardSkin(tone: CardTone): Skin;
  createInputSkin(): Skin;
  createBadgeSkin(tone: BadgeTone): Skin;
}

/** Phần chung: cache sản phẩm theo tham số để component nhận lại đúng object cũ (không re-render thừa). */
abstract class BaseThemeFactory implements UIThemeFactory {
  abstract readonly name: ThemeName;
  protected abstract palette: Palette;
  protected abstract effects: Effects;
  private cache = new Map<string, Skin>();

  createPalette(): Palette {
    return this.palette;
  }

  createEffects(): Effects {
    return this.effects;
  }

  protected memo(key: string, make: () => Skin): Skin {
    let skin = this.cache.get(key);
    if (!skin) {
      skin = make();
      this.cache.set(key, skin);
    }
    return skin;
  }

  createBadgeSkin(tone: BadgeTone): Skin {
    return this.memo(`badge:${tone}`, () => {
      const p = this.palette;
      const color = { neutral: p.textMuted, info: p.accent, success: p.success, warning: p.warning, danger: p.danger }[tone];
      return { "--badge-fg": color, "--badge-bg": `color-mix(in srgb, ${color} 14%, transparent)`,
               "--badge-border": `color-mix(in srgb, ${color} 35%, transparent)` };
    });
  }

  abstract createButtonSkin(variant: ButtonVariant): Skin;
  abstract createCardSkin(tone: CardTone): Skin;
  abstract createInputSkin(): Skin;
}

class NeonDarkFactory extends BaseThemeFactory {
  readonly name = "dark" as const;
  protected palette: Palette = {
    bg: "#0B0D12",
    frame: "#111420",
    surface: "#161A24",
    surface2: "#1E2330",
    border: "rgba(255, 255, 255, 0.08)",
    text: "#EEF1F6",
    textMuted: "#8B94A7",
    accent: "#3DB4FE",
    accent2: "#4CECB8",
    accent3: "#FF4FD8",
    success: "#4CECB8",
    warning: "#FFC24B",
    danger: "#FF5C7A",
    onAccent: "#07131C",
  };
  protected effects: Effects = {
    gradient: "linear-gradient(120deg, #3DB4FE 0%, #4CECB8 100%)",
    glow: "0 0 0 1px rgba(61, 180, 254, 0.28), 0 0 18px rgba(61, 180, 254, 0.18)",
    glowStrong: "0 0 0 1px rgba(76, 236, 184, 0.45), 0 0 28px rgba(76, 236, 184, 0.32)",
    shadow: "0 12px 32px rgba(0, 0, 0, 0.45)",
    focusRing: "0 0 0 3px rgba(61, 180, 254, 0.45)",
  };

  createButtonSkin(variant: ButtonVariant): Skin {
    return this.memo(`btn:${variant}`, () => {
      const p = this.palette, e = this.effects;
      switch (variant) {
        case "primary":
          return { "--btn-bg": e.gradient, "--btn-fg": p.onAccent, "--btn-border": "transparent",
                   "--btn-shadow": e.glow, "--btn-shadow-hover": e.glowStrong };
        case "secondary":
          return { "--btn-bg": p.surface2, "--btn-fg": p.text, "--btn-border": p.border,
                   "--btn-shadow": "none", "--btn-shadow-hover": e.glow };
        case "danger":
          return { "--btn-bg": "rgba(255, 92, 122, 0.12)", "--btn-fg": p.danger, "--btn-border": "rgba(255, 92, 122, 0.4)",
                   "--btn-shadow": "none", "--btn-shadow-hover": "0 0 18px rgba(255, 92, 122, 0.3)" };
        default:
          return { "--btn-bg": "transparent", "--btn-fg": p.textMuted, "--btn-border": "transparent",
                   "--btn-shadow": "none", "--btn-shadow-hover": "none" };
      }
    });
  }

  createCardSkin(tone: CardTone): Skin {
    return this.memo(`card:${tone}`, () => {
      const p = this.palette, e = this.effects;
      if (tone === "accent")
        return { "--card-bg": "linear-gradient(140deg, rgba(61,180,254,0.22), rgba(76,236,184,0.16))",
                 "--card-border": "rgba(76, 236, 184, 0.35)", "--card-shadow": e.glow };
      if (tone === "raised") return { "--card-bg": p.surface2, "--card-border": p.border, "--card-shadow": e.shadow };
      return { "--card-bg": p.surface, "--card-border": p.border, "--card-shadow": "none" };
    });
  }

  createInputSkin(): Skin {
    return this.memo("input", () => ({
      "--input-bg": "#0F121A", "--input-border": "rgba(255, 255, 255, 0.10)",
      "--input-border-focus": this.palette.accent, "--input-ring": this.effects.focusRing,
      "--input-placeholder": "#5D6577",
    }));
  }
}

class NeonLightFactory extends BaseThemeFactory {
  readonly name = "light" as const;
  protected palette: Palette = {
    bg: "#E9ECEB",
    frame: "#2B2E38",     // giống mẫu: khung điều hướng vẫn tối ở theme sáng
    surface: "#FFFFFF",
    surface2: "#F7F8F7",
    border: "rgba(43, 46, 56, 0.09)",
    text: "#2B2E38",
    textMuted: "#6A7180",
    accent: "#1A9EEB",    // đậm hơn #3DB4FE một chút để chữ xanh trên nền trắng đủ tương phản
    accent2: "#18B886",
    accent3: "#D63BB8",
    success: "#14A877",
    warning: "#C98A00",
    danger: "#E0405F",
    onAccent: "#06202B",
  };
  protected effects: Effects = {
    gradient: "linear-gradient(120deg, #3DB4FE 0%, #4CECB8 100%)",
    glow: "0 6px 20px rgba(61, 180, 254, 0.28)",
    glowStrong: "0 8px 28px rgba(76, 236, 184, 0.42)",
    shadow: "0 10px 30px rgba(43, 46, 56, 0.08)",
    focusRing: "0 0 0 3px rgba(61, 180, 254, 0.35)",
  };

  createButtonSkin(variant: ButtonVariant): Skin {
    return this.memo(`btn:${variant}`, () => {
      const p = this.palette, e = this.effects;
      switch (variant) {
        case "primary":
          return { "--btn-bg": e.gradient, "--btn-fg": p.onAccent, "--btn-border": "transparent",
                   "--btn-shadow": e.glow, "--btn-shadow-hover": e.glowStrong };
        case "secondary":
          return { "--btn-bg": p.surface, "--btn-fg": p.text, "--btn-border": p.border,
                   "--btn-shadow": "0 1px 2px rgba(43,46,56,0.06)", "--btn-shadow-hover": "0 4px 14px rgba(43,46,56,0.1)" };
        case "danger":
          return { "--btn-bg": "rgba(224, 64, 95, 0.08)", "--btn-fg": p.danger, "--btn-border": "rgba(224, 64, 95, 0.3)",
                   "--btn-shadow": "none", "--btn-shadow-hover": "0 4px 14px rgba(224, 64, 95, 0.2)" };
        default:
          return { "--btn-bg": "transparent", "--btn-fg": p.textMuted, "--btn-border": "transparent",
                   "--btn-shadow": "none", "--btn-shadow-hover": "none" };
      }
    });
  }

  createCardSkin(tone: CardTone): Skin {
    return this.memo(`card:${tone}`, () => {
      const p = this.palette, e = this.effects;
      if (tone === "accent")
        return { "--card-bg": "linear-gradient(140deg, #3DB4FE 0%, #4CECB8 100%)",
                 "--card-border": "transparent", "--card-shadow": e.glow };
      if (tone === "raised") return { "--card-bg": p.surface, "--card-border": p.border, "--card-shadow": e.shadow };
      return { "--card-bg": p.surface, "--card-border": p.border, "--card-shadow": "none" };
    });
  }

  createInputSkin(): Skin {
    return this.memo("input", () => ({
      "--input-bg": "#F7F8F7", "--input-border": "rgba(43, 46, 56, 0.12)",
      "--input-border-focus": "#3DB4FE", "--input-ring": this.effects.focusRing,
      "--input-placeholder": "#A1A7B3",
    }));
  }
}

export const themeFactories: Record<ThemeName, UIThemeFactory> = {
  dark: new NeonDarkFactory(),
  light: new NeonLightFactory(),
};

/** Biến bảng màu + hiệu ứng thành biến CSS toàn cục (một lần ghi cho cả trang khi đổi theme). */
export function globalVars(f: UIThemeFactory): Record<string, string> {
  const p = f.createPalette(), e = f.createEffects();
  const kebab = (k: string) => k.replace(/[A-Z0-9]/g, (c) => `-${c.toLowerCase()}`);
  const vars: Record<string, string> = {};
  for (const [k, v] of Object.entries(p)) vars[`--c-${kebab(k)}`] = v;
  for (const [k, v] of Object.entries(e)) vars[`--fx-${kebab(k)}`] = v;
  return vars;
}
