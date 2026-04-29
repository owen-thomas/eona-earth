#!/usr/bin/env python3
"""
Implement palette-js.md into eona.html

This script performs three major changes:
1. SHADER UPGRADE — Adds ridgedNoise/ridgedFbm functions, converts renderSurface
   and computeCloudMask into uber-shaders that branch on per-state approach uniforms.
2. UNIFORM WIRING — Adds surfApproach/cloudApproach uniforms to Three.js material
   and setState() function.
3. DATA UPDATE — Replaces all STATES entries with the colour-lab-tuned values from
   palette-js.md, including surfaceApproach and cloudApproach fields.
"""

import re

with open('/home/claude/eona.html', 'r') as f:
    src = f.read()

# ═══════════════════════════════════════════════════════════════════════════
# 1. ADD RIDGED NOISE FUNCTIONS TO SHADER
# ═══════════════════════════════════════════════════════════════════════════
# Insert ridgedNoise and ridgedFbm after the fbm2 function definition.

RIDGED_FUNCTIONS = """
      // === RIDGED MULTIFRACTAL ===
      // Used by topographic surface approach and warped_wisps/ridged_wisps clouds.
      float ridgedNoise(vec3 p) {
        return 1.0 - abs(noise3d(p) * 2.0 - 1.0);
      }
      float ridgedFbm(vec3 p) {
        float v = 0.0, a = 0.5, prev = 1.0;
        for (int i = 0; i < 5; i++) {
          float n = ridgedNoise(p);
          v += a * n * prev;
          prev = n;
          p *= 2.2;
          a *= 0.45;
        }
        return v;
      }
"""

# Insert after fbm2 closing brace
fbm2_end = src.find("return noise3d(p) * 0.65 + noise3d(p * 2.1 + vec3(11.0)) * 0.35;")
fbm2_brace = src.find("}", fbm2_end)
insert_point = fbm2_brace + 1
src = src[:insert_point] + "\n" + RIDGED_FUNCTIONS + src[insert_point:]


# ═══════════════════════════════════════════════════════════════════════════
# 2. ADD APPROACH UNIFORM DECLARATIONS TO SHADER
# ═══════════════════════════════════════════════════════════════════════════
# Add aSurfApproach, bSurfApproach, aCloudApproach, bCloudApproach as floats.
# Encoding: surface: 0=screenprint, 1=watercolor, 2=topographic
#           cloud:   0=warped, 1=ridged_wisps, 2=warped_layers, 3=warped_wisps

approach_uniforms = """
      // Surface approach: 0.0=screenprint, 1.0=watercolor, 2.0=topographic
      uniform float aSurfApproach, bSurfApproach;
      // Cloud approach: 0.0=warped, 1.0=ridged_wisps, 2.0=warped_layers, 3.0=warped_wisps
      uniform float aCloudApproach, bCloudApproach;
"""

# Insert after the existing noiseThresh uniform declarations
thresh_decl = "uniform float aNoiseThresh1, aNoiseThresh2;"
thresh_pos = src.find(thresh_decl)
thresh_line_end = src.find("\n", thresh_pos + len(thresh_decl) + 1)
# Find the bNoiseThresh line
bthresh_decl = "uniform float bNoiseThresh1, bNoiseThresh2;"
bthresh_pos = src.find(bthresh_decl, thresh_pos)
bthresh_line_end = src.find("\n", bthresh_pos)
src = src[:bthresh_line_end + 1] + approach_uniforms + src[bthresh_line_end + 1:]


# ═══════════════════════════════════════════════════════════════════════════
# 3. REPLACE renderSurface WITH UBER-SHADER VERSION
# ═══════════════════════════════════════════════════════════════════════════
# The new version accepts a surfApproach float and branches.

OLD_RENDER_SURFACE_START = "      // === RENDER ONE STATE (surface only — no clouds/ice) ==="
OLD_RENDER_SURFACE_END = "return mix(noiseCol, dataCol, useLandSea);\n      }"

rs_start = src.find(OLD_RENDER_SURFACE_START)
rs_end = src.find(OLD_RENDER_SURFACE_END, rs_start)
rs_end += len(OLD_RENDER_SURFACE_END)

NEW_RENDER_SURFACE = """      // === RENDER ONE STATE (surface only — no clouds/ice) ===
      // Uber-shader: surfApproach selects the noise shaping.
      // 0.0 = screenprint (hard-edged riso ink zones)
      // 1.0 = watercolor  (domain-warped, wide smoothstep bleed)
      // 2.0 = topographic (ridged multifractal with contour lines)
      // The SDF data-driven path (useLandSea > 0) always uses screenprint
      // noise for land/sea modulation regardless of surfApproach.
      vec3 renderSurface(
        vec3 p,
        vec3 c0, vec3 c1, vec3 c2, vec3 c3,
        float surfIntens, float seed,
        float sdfSample, float useLandSea, float coastSoft,
        float noiseThresh1,
        float noiseThresh2,
        float surfApproach
      ) {
        vec3 sOff = vec3(seed * 13.7, seed * 7.3, seed * 19.1);

        float s1 = clamp(noiseThresh1, 0.04, 0.94);
        float s2 = clamp(noiseThresh2, 0.04, 0.97);
        float shape1, shape2, overlap;
        vec3 noiseSurf;

        if (surfApproach < 0.5) {
          // === SCREENPRINT ===
          float n1 = fbm(p * 2.4 + sOff);
          float n2 = fbm(p * 4.6 + sOff * 1.3 + vec3(100.0));
          shape1 = smoothstep(s1 - 0.04, s1 + 0.04, n1);
          shape2 = smoothstep(s2 - 0.04, s2 + 0.04, n2);
          overlap = shape1 * shape2;
          noiseSurf = c3;
          noiseSurf = mix(noiseSurf, c2, shape1);
          noiseSurf = mix(noiseSurf, c1, shape2 * 0.85);
          noiseSurf *= mix(1.0, 0.86, overlap);
        } else if (surfApproach < 1.5) {
          // === WATERCOLOR ===
          vec3 warp = vec3(
            fbm(p * 1.6 + sOff) - 0.5,
            fbm(p * 1.6 + sOff + vec3(50.0)) - 0.5,
            fbm(p * 1.6 + sOff + vec3(100.0)) - 0.5
          );
          vec3 wp = p + warp * 0.35;
          float n1 = fbm(wp * 2.4 + sOff);
          float n2 = fbm(wp * 3.2 + sOff * 1.3 + vec3(100.0));
          shape1 = smoothstep(s1 - 0.18, s1 + 0.18, n1);
          shape2 = smoothstep(s2 - 0.18, s2 + 0.18, n2);
          overlap = shape1 * shape2;
          noiseSurf = c3;
          noiseSurf = mix(noiseSurf, c2, shape1);
          noiseSurf = mix(noiseSurf, c1, shape2 * 0.80);
        } else {
          // === TOPOGRAPHIC ===
          float n1 = ridgedFbm(p * 2.0 + sOff);
          float n2 = ridgedFbm(p * 3.5 + sOff + vec3(50.0));
          shape1 = smoothstep(s1 - 0.04, s1 + 0.04, n1);
          shape2 = smoothstep(s2 - 0.04, s2 + 0.04, n2);
          float contour = smoothstep(0.02, 0.0, abs(fract(n1 * 6.0) - 0.5));
          contour += smoothstep(0.02, 0.0, abs(fract(n2 * 5.0) - 0.5)) * 0.5;
          overlap = shape1 * shape2;
          noiseSurf = c3;
          noiseSurf = mix(noiseSurf, c2, shape1);
          noiseSurf = mix(noiseSurf, c1, shape2 * 0.85);
          noiseSurf *= 1.0 - contour * 0.12;
        }

        vec3 noiseCol = mix(c2, noiseSurf, surfIntens);

        // === DATA-DRIVEN LAND/SEA PATH ===
        float seaMod  = mix(1.0, 0.93, shape1);
        float landMod = mix(1.0, 0.93, shape1);
        vec3 seaCol  = c2 * seaMod;
        vec3 landCol = c1 * landMod;
        float landness = smoothstep(0.5 - coastSoft, 0.5 + coastSoft, sdfSample);
        vec3 dataCol = mix(seaCol, landCol, landness);

        return mix(noiseCol, dataCol, useLandSea);
      }"""

src = src[:rs_start] + NEW_RENDER_SURFACE + src[rs_end:]


# ═══════════════════════════════════════════════════════════════════════════
# 4. REPLACE computeCloudMask WITH UBER-SHADER VERSION
# ═══════════════════════════════════════════════════════════════════════════

OLD_CLOUD_START = "      // === CLOUD MASK ==="
OLD_CLOUD_END = "return mask;\n      }"

# Find the cloud mask function
cm_start = src.find(OLD_CLOUD_START)
cm_end_marker = "mask *= 1.0 + 0.05 * sin(time * 0.18);"
cm_end_pos = src.find(cm_end_marker, cm_start)
# Find the closing "return mask;\n      }" after that
cm_return = src.find("return mask;", cm_end_pos)
cm_close = src.find("}", cm_return)
cm_end = cm_close + 1

NEW_CLOUD_MASK = """      // === CLOUD MASK ===
      // Uber-shader: cloudApproach selects the cloud generation algorithm.
      // 0.0 = warped         (domain-warped fbm, good bands and swirls)
      // 1.0 = ridged_wisps   (ridged multifractal, cirrus-like)
      // 2.0 = warped_layers  (three transparent fbm layers at different scales)
      // 3.0 = warped_wisps   (warped body + ridged detail + edge erosion)
      float computeCloudMask(vec3 p, float cloudDens, float cloudShp, float seed, float cloudApproach) {
        if (cloudDens < 0.001) return 0.0;
        vec3 cp = rotateY(p, cloudRotation);
        vec3 sOff = vec3(seed * 13.7, seed * 7.3, seed * 19.1)
                  + vec3(time * 0.004, time * 0.003, time * 0.0025);
        float yAniso = mix(3.0, 1.0, cloudShp);
        float latFade = 1.0 - pow(abs(cp.y), 3.0) * 0.25;
        float mask = 0.0;

        if (cloudApproach < 0.5) {
          // === WARPED ===
          float warpStrength = mix(0.35, 1.6, cloudShp);
          vec3 warp = vec3(
            fbm(cp * 1.8 + sOff),
            fbm(cp * 1.8 + sOff + vec3(13.1)),
            fbm(cp * 1.8 + sOff + vec3(27.7))
          ) - 0.5;
          vec3 sp = vec3(cp.x + sOff.x * 0.2, cp.y * yAniso, cp.z + sOff.y * 0.2) + warp * warpStrength;
          float cA = fbm2(sp * 2.0);
          vec3 sp2 = vec3(cp.x * 0.7, cp.y * yAniso * 0.55, cp.z * 0.7) + warp * warpStrength * 0.6;
          float cB = fbm2(sp2 + sOff * 0.1);
          float cC = fbm(cp * 6.5 + sOff * 0.7 + vec3(55.0));
          float field = cA * 0.60 + cB * 0.30 + cC * 0.18;
          float thresh = mix(0.78, 0.18, cloudDens);
          mask = smoothstep(thresh, thresh + 0.04, field) * latFade;

        } else if (cloudApproach < 1.5) {
          // === RIDGED WISPS ===
          float yStretch = mix(2.0, 1.0, cloudShp);
          vec3 sp = vec3(cp.x, cp.y * yStretch, cp.z);
          float warpN = noise3d(sp * 1.5 + sOff);
          sp += vec3(warpN - 0.5) * mix(0.2, 0.7, cloudShp) * 0.4;
          float field = ridgedFbm(sp * 2.5 + sOff);
          float thresh = mix(0.72, 0.12, cloudDens);
          mask = smoothstep(thresh, thresh + 0.06, field) * latFade;

        } else if (cloudApproach < 2.5) {
          // === WARPED LAYERS ===
          float yAni = mix(2.5, 1.0, cloudShp);
          float warpAmt = mix(0.25, 0.7, cloudShp);
          vec3 off1 = vec3(time * 0.005, time * 0.003, time * 0.004);
          vec3 off2 = vec3(time * 0.003, time * 0.005, time * 0.002) + vec3(30.0);
          vec3 off3 = vec3(time * 0.002, time * 0.004, time * 0.006) + vec3(60.0);

          // Layer helper inlined (can't call sub-functions easily in uber-shader)
          // Layer 1
          vec3 sp1 = vec3(cp.x, cp.y * yAni, cp.z) * 1.6 + off1;
          float w1a = noise3d(sp1 * 0.7 + off1) - 0.5;
          float w1b = noise3d(sp1 * 0.7 + off1 + vec3(17.0)) - 0.5;
          sp1.x += w1a * warpAmt; sp1.z += w1b * warpAmt;
          float l1 = fbm2(sp1);
          // Layer 2
          vec3 sp2 = vec3(cp.x, cp.y * yAni * 0.8, cp.z) * 3.0 + off2;
          float w2a = noise3d(sp2 * 0.7 + off2) - 0.5;
          float w2b = noise3d(sp2 * 0.7 + off2 + vec3(17.0)) - 0.5;
          sp2.x += w2a * warpAmt * 0.8; sp2.z += w2b * warpAmt * 0.8;
          float l2 = fbm2(sp2);
          // Layer 3
          vec3 sp3 = vec3(cp.x, cp.y * yAni * 0.6, cp.z) * 5.5 + off3;
          float w3a = noise3d(sp3 * 0.7 + off3) - 0.5;
          float w3b = noise3d(sp3 * 0.7 + off3 + vec3(17.0)) - 0.5;
          sp3.x += w3a * warpAmt * 0.5; sp3.z += w3b * warpAmt * 0.5;
          float l3 = fbm2(sp3);

          float tBase = mix(0.72, 0.06, cloudDens * cloudDens * 0.6 + cloudDens * 0.4);
          float stagger = mix(0.12, 0.005, cloudDens);
          float edgeW = mix(0.14, 0.03, cloudDens);
          float m1 = smoothstep(tBase, tBase + edgeW, l1);
          float m2 = smoothstep(tBase + stagger, tBase + stagger + edgeW * 0.8, l2);
          float m3 = smoothstep(tBase + stagger * 2.0, tBase + stagger * 2.0 + edgeW * 0.6, l3);
          float w1m = mix(0.45, 0.92, cloudDens);
          float w2m = mix(0.28, 0.80, cloudDens);
          float w3m = mix(0.18, 0.70, cloudDens);
          float combined = 1.0 - (1.0 - m1 * w1m) * (1.0 - m2 * w2m) * (1.0 - m3 * w3m);
          mask = combined * latFade;

        } else {
          // === WARPED WISPS ===
          float warpStrength = mix(0.35, 1.6, cloudShp);
          vec3 warp = vec3(
            fbm(cp * 1.8 + sOff),
            fbm(cp * 1.8 + sOff + vec3(13.1)),
            fbm(cp * 1.8 + sOff + vec3(27.7))
          ) - 0.5;
          vec3 sp = vec3(cp.x + sOff.x * 0.2, cp.y * yAniso, cp.z + sOff.y * 0.2) + warp * warpStrength;
          float cA = fbm2(sp * 2.0);
          vec3 sp2 = vec3(cp.x * 0.7, cp.y * yAniso * 0.55, cp.z * 0.7) + warp * warpStrength * 0.6;
          float cB = fbm2(sp2 + sOff * 0.1);
          // Ridged detail layer
          float yStr = mix(1.6, 1.0, cloudShp);
          vec3 rp = vec3(sp.x, sp.y * yStr, sp.z);
          float ridgeDetail = ridgedFbm(rp * 3.0 + sOff * 0.6);
          float field = cA * 0.48 + cB * 0.22 + ridgeDetail * 0.30;
          // Edge erosion
          float erosion = ridgedFbm(cp * 5.0 + sOff * 0.4 + vec3(42.0));
          field = field * (0.7 + erosion * 0.3);
          float thresh = mix(0.78, 0.18, cloudDens);
          mask = smoothstep(thresh, thresh + 0.06, field) * latFade;
        }

        // Subtle opacity pulse — ±5% over ~35 s period
        mask *= 1.0 + 0.05 * sin(time * 0.18);
        return mask;
      }"""

src = src[:cm_start] + NEW_CLOUD_MASK + src[cm_end:]


# ═══════════════════════════════════════════════════════════════════════════
# 5. UPDATE renderSurface() CALLS TO PASS surfApproach
# ═══════════════════════════════════════════════════════════════════════════
# The main() calls renderSurface twice — add the approach parameter.

src = src.replace(
    "vec3 colA = renderSurface(p, aC0, aC1, aC2, aC3, aSurfIntens, aSeed, sdfSample, aUseLandSea, aCoastSoft, aNoiseThresh1, aNoiseThresh2);",
    "vec3 colA = renderSurface(p, aC0, aC1, aC2, aC3, aSurfIntens, aSeed, sdfSample, aUseLandSea, aCoastSoft, aNoiseThresh1, aNoiseThresh2, aSurfApproach);"
)
src = src.replace(
    "vec3 colB = renderSurface(p, bC0, bC1, bC2, bC3, bSurfIntens, bSeed, sdfSample, bUseLandSea, bCoastSoft, bNoiseThresh1, bNoiseThresh2);",
    "vec3 colB = renderSurface(p, bC0, bC1, bC2, bC3, bSurfIntens, bSeed, sdfSample, bUseLandSea, bCoastSoft, bNoiseThresh1, bNoiseThresh2, bSurfApproach);"
)


# ═══════════════════════════════════════════════════════════════════════════
# 6. UPDATE computeCloudMask() CALLS TO PASS cloudApproach
# ═══════════════════════════════════════════════════════════════════════════

src = src.replace(
    "float cloudMaskA = computeCloudMask(p, aCloudDens, aCloudShape, aSeed);",
    "float cloudMaskA = computeCloudMask(p, aCloudDens, aCloudShape, aSeed, aCloudApproach);"
)
src = src.replace(
    "float cloudMaskB = computeCloudMask(p, bCloudDens, bCloudShape, bSeed);",
    "float cloudMaskB = computeCloudMask(p, bCloudDens, bCloudShape, bSeed, bCloudApproach);"
)


# ═══════════════════════════════════════════════════════════════════════════
# 7. ADD APPROACH UNIFORMS TO THREE.JS MATERIAL
# ═══════════════════════════════════════════════════════════════════════════

# Add to the uniform block after bNoiseThresh2
src = src.replace(
    "bNoiseThresh2: { value: s0.noiseThresh2 ?? 0.56 }\n        }",
    """bNoiseThresh2: { value: s0.noiseThresh2 ?? 0.56 },

          // Surface/cloud approach selectors (float-encoded)
          aSurfApproach:  { value: 0.0 },
          bSurfApproach:  { value: 0.0 },
          aCloudApproach: { value: 3.0 },
          bCloudApproach: { value: 3.0 }
        }"""
)


# ═══════════════════════════════════════════════════════════════════════════
# 8. WIRE APPROACH VALUES IN setState()
# ═══════════════════════════════════════════════════════════════════════════
# Add approach encoding map and setState lines.

# Insert the encoding map before the setState function
APPROACH_MAP = """
      // Encode approach strings → shader float IDs
      const SURF_APPROACH_ID = { screenprint: 0.0, watercolor: 1.0, topographic: 2.0 };
      const CLOUD_APPROACH_ID = { warped: 0.0, ridged_wisps: 1.0, warped_layers: 2.0, warped_wisps: 3.0 };
"""

# Find setState function
set_state_marker = "function setState(prefix, S) {"
ss_pos = src.find(set_state_marker)
# Insert the map just before this function
src = src[:ss_pos] + APPROACH_MAP + "\n      " + src[ss_pos:]

# Add approach lines to setState body — after the NoiseThresh2 line
src = src.replace(
    "u[prefix + 'NoiseThresh2'].value = S.noiseThresh2 ?? 0.56;\n      }",
    """u[prefix + 'NoiseThresh2'].value = S.noiseThresh2 ?? 0.56;
        u[prefix + 'SurfApproach'].value  = SURF_APPROACH_ID[S.surfaceApproach ?? 'screenprint'] ?? 0.0;
        u[prefix + 'CloudApproach'].value = CLOUD_APPROACH_ID[S.cloudApproach ?? 'warped_wisps'] ?? 3.0;
      }"""
)


# ═══════════════════════════════════════════════════════════════════════════
# 9. REPLACE ALL STATES WITH PALETTE-JS.MD VALUES
# ═══════════════════════════════════════════════════════════════════════════

NEW_STATES = """    const STATES = [
      // === 01 · Molten Hadean (early) — 4540–4420 Ma ===
      { name: 'Molten Hadean (early)',
        span: [4540, 4420], blendStart: 4540,
        palette: ['#2D2D2D','#E34E2A','#3C0E04','#8F220F','#1E0F01'],
        noiseThresh1: 0.80, noiseThresh2: 0.79, surfaceIntensity: 0.77,
        glowColor: '#8F220F', glowStrength: 0.80,
        hazeColor: '#E34E2A', hazeOpacity: 0.57,
        darkHazeColor: '#1A0808', darkHazeOpacity: 0.56,
        cloudDensity: 0.00, cloudShape: 1.00, polarIce: 0.0, seed: 1.3,
        useLandSea: 0.0, coastSoftness: 0.01,
        surfaceApproach: 'topographic', cloudApproach: 'warped_layers' },

      // === 01 · Molten Hadean (late) — 4420–4300 Ma ===
      { name: 'Molten Hadean (late)',
        span: [4420, 4300], blendStart: 4320,
        palette: ['#2D2D2D','#E34E2A','#8F220F','#3C0E04','#1E0F01'],
        noiseThresh1: 0.75, noiseThresh2: 0.78, surfaceIntensity: 1.00,
        glowColor: '#8F220F', glowStrength: 0.55,
        hazeColor: '#8E3A20', hazeOpacity: 0.16,
        darkHazeColor: '#1F0F0A', darkHazeOpacity: 0.48,
        cloudDensity: 0.00, cloudShape: 0.00, polarIce: 0.0, seed: 1.3,
        useLandSea: 0.0, coastSoftness: 0.01,
        surfaceApproach: 'topographic', cloudApproach: 'warped_layers' },

      // === 02 · Steam World — 4300–4000 Ma ===
      { name: 'Steam world',
        span: [4300, 4000], blendStart: 4060,
        palette: ['#E8D9C5','#8B5E3C','#636363','#3D3D3D','#0D1611'],
        noiseThresh1: 0.45, noiseThresh2: 0.59, surfaceIntensity: 0.65,
        glowColor: '#8F220F', glowStrength: 0.20,
        hazeColor: '#C7B299', hazeOpacity: 0.43,
        darkHazeColor: '#241E18', darkHazeOpacity: 0.82,
        cloudDensity: 0.70, cloudShape: 0.00, polarIce: 0.0, seed: 2.7,
        useLandSea: 0.0, coastSoftness: 0.01,
        surfaceApproach: 'watercolor', cloudApproach: 'warped_layers' },

      // === 03 · Hazy Archean (early) — 4000–3200 Ma ===
      { name: 'Hazy Archean (early)',
        span: [4000, 3200], blendStart: 4000,
        palette: ['#F2E7D5','#4A3B2C','#1C6055','#123D36','#060A0B'],
        noiseThresh1: 0.50, noiseThresh2: 0.65, surfaceIntensity: 0.70,
        glowStrength: 0.0,
        hazeColor: '#A8C3BC', hazeOpacity: 0.52,
        darkHazeColor: '#0A1A17', darkHazeOpacity: 0.83,
        cloudDensity: 0.50, cloudShape: 0.00, polarIce: 0.0, seed: 3.1,
        useLandSea: 0.0, coastSoftness: 0.01,
        surfaceApproach: 'screenprint', cloudApproach: 'warped_layers' },

      // === 04 · Hazy Archean (late) — 3200–2500 Ma ===
      { name: 'Hazy Archean (late)',
        span: [3200, 2500], blendStart: 2530,
        palette: ['#EBC9C9','#5E503F','#1C6055','#123D36','#060E09'],
        noiseThresh1: 0.50, noiseThresh2: 0.65, surfaceIntensity: 0.68,
        glowStrength: 0.0,
        hazeColor: '#E5B3B3', hazeOpacity: 0.42,
        darkHazeColor: '#0E1F1C', darkHazeOpacity: 0.70,
        cloudDensity: 0.36, cloudShape: 0.00, polarIce: 0.0, seed: 3.8,
        useLandSea: 0.0, coastSoftness: 0.01,
        surfaceApproach: 'screenprint', cloudApproach: 'warped' },

      // === 05 · Great Oxidation (early) — 2500–2400 Ma ===
      { name: 'Great Oxidation (early)',
        span: [2500, 2400], blendStart: 2500,
        palette: ['#F8F9FA','#745A3D','#2D6A4F','#1B4332','#131A09'],
        noiseThresh1: 0.50, noiseThresh2: 0.65, surfaceIntensity: 0.75,
        glowStrength: 0.0,
        hazeColor: '#B7CEB0', hazeOpacity: 0.42,
        darkHazeColor: '#141C16', darkHazeOpacity: 0.50,
        cloudDensity: 0.37, cloudShape: 0.00, polarIce: 0.0, seed: 4.5,
        useLandSea: 0.0, coastSoftness: 0.01,
        surfaceApproach: 'screenprint', cloudApproach: 'warped_layers' },

      // === 05 · Great Oxidation (late) — 2400–2300 Ma ===
      { name: 'Great Oxidation (late)',
        span: [2400, 2300], blendStart: 2302,
        palette: ['#FFFFFF','#8B5E3C','#1E6091','#184E77','#091420'],
        noiseThresh1: 0.50, noiseThresh2: 0.65, surfaceIntensity: 0.75,
        glowStrength: 0.0,
        hazeColor: '#A9D6E5', hazeOpacity: 0.33,
        darkHazeColor: '#0D111A', darkHazeOpacity: 0.40,
        cloudDensity: 0.27, cloudShape: 0.00, polarIce: 0.0, seed: 4.7,
        useLandSea: 0.0, coastSoftness: 0.01,
        surfaceApproach: 'screenprint', cloudApproach: 'warped' },

      // === 06 · Huronian Snowball — 2300–2100 Ma ===
      { name: 'Huronian snowball',
        span: [2300, 2100], blendStart: 2105,
        palette: ['#F1F3F5','#ADB5BD','#E9ECEF','#DEE2E6','#0E141B'],
        noiseThresh1: 0.50, noiseThresh2: 0.65, surfaceIntensity: 0.32,
        glowStrength: 0.0,
        hazeColor: '#D1DCE5', hazeOpacity: 0.50,
        darkHazeColor: '#1C1E21', darkHazeOpacity: 0.60,
        cloudDensity: 0.46, cloudShape: 0.00, polarIce: 0.0, seed: 5.1,
        useLandSea: 0.0, coastSoftness: 0.01,
        surfaceApproach: 'screenprint', cloudApproach: 'warped_layers' },

      // === 07 · Boring Billion (early) — 2100–1500 Ma ===
      { name: 'Boring Billion (early)',
        span: [2100, 1500], blendStart: 2100,
        palette: ['#FDFCF0','#84A59D','#4B7074','#325357','#060D0A'],
        noiseThresh1: 0.50, noiseThresh2: 0.62, surfaceIntensity: 0.62,
        glowStrength: 0.0,
        hazeColor: '#C9CBA3', hazeOpacity: 0.26,
        darkHazeColor: '#1D1D1B', darkHazeOpacity: 0.45,
        cloudDensity: 0.38, cloudShape: 0.00, polarIce: 0.0, seed: 6.0,
        useLandSea: 0.0, coastSoftness: 0.01,
        surfaceApproach: 'screenprint', cloudApproach: 'warped_layers' },

      // === 08 · Boring Billion (mid) — 1500–1000 Ma ===
      { name: 'Boring Billion (mid)',
        span: [1500, 1000], blendStart: 1500,
        palette: ['#FDFCF0','#918151','#4B7074','#325357','#070D11'],
        noiseThresh1: 0.50, noiseThresh2: 0.62, surfaceIntensity: 0.60,
        glowStrength: 0.0,
        hazeColor: '#BDBF95', hazeOpacity: 0.25,
        darkHazeColor: '#1F1E1C', darkHazeOpacity: 0.35,
        cloudDensity: 0.25, cloudShape: 0.00, polarIce: 0.0, seed: 6.4,
        useLandSea: 0.0, coastSoftness: 0.01,
        surfaceApproach: 'screenprint', cloudApproach: 'warped_layers' },

      // === 09 · Boring Billion (late) — 1000–720 Ma ===
      { name: 'Boring Billion (late)',
        span: [1000, 720], blendStart: 722,
        palette: ['#FDFCF0','#A89F91','#5E6E89','#41526F','#06091E'],
        noiseThresh1: 0.50, noiseThresh2: 0.62, surfaceIntensity: 0.58,
        glowStrength: 0.0,
        hazeColor: '#A5A58D', hazeOpacity: 0.35,
        darkHazeColor: '#1E1F21', darkHazeOpacity: 0.45,
        cloudDensity: 0.15, cloudShape: 0.00, polarIce: 0.0, seed: 6.8,
        useLandSea: 0.0, coastSoftness: 0.01,
        surfaceApproach: 'screenprint', cloudApproach: 'warped' },

      // === 10 · Cryogenian Snowball — 720–635 Ma ===
      { name: 'Cryogenian snowball',
        span: [720, 635], blendStart: 637,
        palette: ['#EEF4F7','#98C1D9','#C7EDEF','#E0FBFC','#0A1428'],
        noiseThresh1: 0.50, noiseThresh2: 0.65, surfaceIntensity: 0.28,
        glowStrength: 0.0,
        hazeColor: '#BDE0FE', hazeOpacity: 0.48,
        darkHazeColor: '#151821', darkHazeOpacity: 0.65,
        cloudDensity: 0.43, cloudShape: 0.00, polarIce: 0.0, seed: 7.3,
        useLandSea: 0.35, coastSoftness: 0.01,
        surfaceApproach: 'screenprint', cloudApproach: 'warped' },

      // === 11 · Hothouse World — 635–400 Ma ===
      { name: 'Hothouse world',
        span: [635, 400], blendStart: 470,
        palette: ['#F2E8CF','#4F8D5C','#006831','#004B23','#032832'],
        noiseThresh1: 0.46, noiseThresh2: 0.56, surfaceIntensity: 0.78,
        glowStrength: 0.0,
        hazeColor: '#95D5B2', hazeOpacity: 0.45,
        darkHazeColor: '#08140D', darkHazeOpacity: 0.55,
        cloudDensity: 0.56, cloudShape: 0.45, polarIce: 0.0, seed: 8.4,
        useLandSea: 1.0, coastSoftness: 0.01,
        surfaceApproach: 'screenprint', cloudApproach: 'warped_wisps' },

      // === 12 · Green World — 400–66 Ma ===
      { name: 'Green world',
        span: [400, 66], blendStart: 400,
        palette: ['#F2E8CF','#6A994E','#045F31','#003E1F','#011F15'],
        noiseThresh1: 0.46, noiseThresh2: 0.56, surfaceIntensity: 0.88,
        glowStrength: 0.0,
        hazeColor: '#74C69D', hazeOpacity: 0.30,
        darkHazeColor: '#051208', darkHazeOpacity: 0.40,
        cloudDensity: 0.46, cloudShape: 0.50, polarIce: 0.0, seed: 9.1,
        useLandSea: 1.0, coastSoftness: 0.01,
        surfaceApproach: 'screenprint', cloudApproach: 'warped_wisps' },

      // === 13 · Modern Earth — 66–0 Ma ===
      { name: 'Modern Earth',
        span: [66, 0], blendStart: 0,
        palette: ['#F8F9FA','#4DAE82','#0085CB','#0077B6','#041528'],
        noiseThresh1: 0.46, noiseThresh2: 0.56, surfaceIntensity: 0.82,
        glowStrength: 0.0,
        hazeColor: '#CAF0F8', hazeOpacity: 0.08,
        darkHazeColor: '#020408', darkHazeOpacity: 0.30,
        cloudDensity: 0.46, cloudShape: 1.00, polarIce: 0.85, seed: 10.5,
        useLandSea: 1.0, coastSoftness: 0.01,
        surfaceApproach: 'screenprint', cloudApproach: 'warped_wisps' }
    ];"""

# Find and replace the entire STATES array
states_start = src.find("    const STATES = [")
states_end = src.find("    ];", states_start) + len("    ];")
src = src[:states_start] + NEW_STATES + src[states_end:]


# ═══════════════════════════════════════════════════════════════════════════
# WRITE OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

with open('/home/claude/eona.html', 'w') as f:
    f.write(src)

print("✓ palette-js.md implemented successfully")
print("  → ridgedNoise / ridgedFbm added to shader")
print("  → renderSurface uber-shader: screenprint | watercolor | topographic")
print("  → computeCloudMask uber-shader: warped | ridged_wisps | warped_layers | warped_wisps")
print("  → approach uniforms added to Three.js material + setState()")
print("  → all 15 STATES updated with colour-lab-tuned values")
