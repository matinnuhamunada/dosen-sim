// Three.js campus: one zone per activity; characters walk between zones in proportion to
// their logged weekly hours. Animation is a pure function of (semester, tau) so scrubbing
// is deterministic and never touches simulation data.
//
// Look: light isometric "strategy game" (pale ground, white buildings, coloured roofs,
// soft shadows); camera pans with left drag, rotates with right drag, zooms with the wheel.

import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { type Agent, type KeyEvent, type Run, isPresent, semAt } from "./log";

export const ZONES: Record<string, { label: string; icon: string; color: number; pos: [number, number] }> = {
  teaching: { label: "Lecture hall", icon: "🎓", color: 0x2f6bff, pos: [-8, -6] },
  research: { label: "Lab", icon: "🔬", color: 0x14b8a6, pos: [0, -9] },
  supervision: { label: "Supervision room", icon: "🧑‍🏫", color: 0x0ea5e9, pos: [8, -6] },
  community_service: { label: "Village hall", icon: "🏘️", color: 0x84cc16, pos: [-10, 3] },
  admin: { label: "Admin building", icon: "🗂️", color: 0x64748b, pos: [10, 3] },
  external: { label: "Consulting office", icon: "💼", color: 0xf59e0b, pos: [5, 10] },
  rest: { label: "Café / home", icon: "☕", color: 0xec4899, pos: [-5, 10] },
};
const ORDER = ["teaching", "research", "supervision", "community_service", "admin", "external", "rest"];

export const ARCHETYPE_COLORS: Record<string, string> = {
  research_maximiser: "#14b8a6",
  teaching_loyalist: "#6366f1",
  admin_climber: "#64748b",
  external_earner: "#f59e0b",
  balanced_strategist: "#ec4899",
  none: "#f97316",
};
export const PIN_COLORS = ["#ef4444", "#0ea5e9", "#eab308"];
export const SELECT_COLOR = "#2f6bff";

const C = {
  bg: 0xe8eef5,
  ground: 0xe3eaf1,
  edge: 0xd5dee8,
  grass: 0xd3e8da,
  pad: 0xe9eef4,
  road: 0xc3cdd9,
  line: 0xffffff,
  wall: 0xf8fafc,
  window: 0xdbe6f7,
  trunk: 0xb69a7c,
  leaf: [0x8fd1ad, 0x76c49d, 0xa6dcc0, 0x86cba9],
};

const CUE_ICONS: Partial<Record<KeyEvent["kind"], string>> = {
  paper: "📄",
  promotion: "⭐",
  grant: "💰",
  role: "🏷️",
  committee: "📋",
  coauthor: "🤝",
  attrition: "🚪",
  retirement: "🎓",
  mentor: "🧑‍🏫",
  hire: "👋",
  certified: "📜",
};
const WALK = 0.18; // fraction of each segment spent walking
const CUE_LIFE = 0.45; // cues fade over this fraction of a semester
const POLAR = 0.96; // isometric tilt from vertical (≈ atan √2)
const HOME_AZIMUTH = Math.PI / 4;
const MAP_LIMIT = 18; // camera target stays within this square
const BUILDING_OUT = 3.4; // building sits this far behind its gathering spot
const CROWD = 24; // above this many lecturers, hide unfocused name tags

export type CameraCommand = "in" | "out" | "left" | "right" | "home";

function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return (h >>> 0) / 4294967296;
}

function hex(n: number): string {
  return `#${n.toString(16).padStart(6, "0")}`;
}

interface PillStyle {
  size?: number;
  bg?: string;
  fg?: string;
  border?: string;
}

function drawPill(canvas: HTMLCanvasElement, text: string, o: PillStyle): void {
  const size = o.size ?? 28;
  const font = `600 ${size}px Inter, system-ui, sans-serif`;
  const ctx = canvas.getContext("2d")!;
  ctx.font = font;
  const w = Math.ceil(ctx.measureText(text).width) + 28;
  const h = size + 18;
  canvas.width = w + 4;
  canvas.height = h + 6;
  ctx.font = font;
  ctx.shadowColor = "rgba(15,26,46,0.18)";
  ctx.shadowBlur = 4;
  ctx.shadowOffsetY = 2;
  ctx.fillStyle = o.bg ?? "#ffffff";
  ctx.beginPath();
  ctx.roundRect(2, 1, w, h, h / 2);
  ctx.fill();
  ctx.shadowColor = "transparent";
  if (o.border) {
    ctx.strokeStyle = o.border;
    ctx.lineWidth = 2;
    ctx.stroke();
  }
  ctx.fillStyle = o.fg ?? "#0f1a2e";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 16, 1 + h / 2 + 1);
}

function textSprite(text: string, opts: PillStyle = {}): THREE.Sprite {
  const canvas = document.createElement("canvas");
  drawPill(canvas, text, opts);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  sizeSprite(sprite, canvas);
  sprite.renderOrder = 10;
  return sprite;
}

function sizeSprite(sprite: THREE.Sprite, canvas: HTMLCanvasElement): void {
  const scale = 0.016;
  sprite.scale.set(canvas.width * scale, canvas.height * scale, 1);
}

function setSpriteText(sprite: THREE.Sprite, text: string, opts: PillStyle): void {
  const tex = sprite.material.map as THREE.CanvasTexture;
  const canvas = tex.image as HTMLCanvasElement;
  drawPill(canvas, text, opts);
  tex.dispose(); // canvas size may change: force re-upload
  sizeSprite(sprite, canvas);
  tex.needsUpdate = true;
}

const NAME_STYLE: PillStyle = { size: 22, bg: "#1e293b", fg: "#ffffff" };
const NAME_SELECTED: PillStyle = { size: 24, bg: SELECT_COLOR, fg: "#ffffff" };

interface Character {
  group: THREE.Group;
  body: THREE.MeshStandardMaterial;
  head: THREE.MeshStandardMaterial;
  badge: THREE.Group;
  ring: THREE.Mesh;
  label: THREE.Sprite;
  labelText: string;
  base: THREE.Color;
  rankShown: number;
}

export interface Focus {
  selected: string | null;
  pinned: string[];
  trail: boolean;
}

export class CampusScene {
  readonly renderer: THREE.WebGLRenderer;
  readonly scene = new THREE.Scene();
  readonly camera: THREE.OrthographicCamera;
  readonly controls: OrbitControls;
  private chars = new Map<string, Character>();
  private cues: { sprite: THREE.Sprite; agent: string; offset: number }[] = [];
  private cueKey = "";
  private trails = new Map<string, THREE.Line>();
  private run: Run | null = null;
  private raycaster = new THREE.Raycaster();
  // camera animation
  private follow = false;
  private lastSelected: string | null = null;
  private zoomGoal: number | null = null;
  private rotLeft = 0;
  private panGoal: THREE.Vector3 | null = null;

  constructor(private container: HTMLElement, onPick: (id: string | null) => void) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(this.renderer.domElement);
    this.scene.background = new THREE.Color(C.bg);
    this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 500);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.screenSpacePanning = false; // pan along the ground like an RTS
    this.controls.minPolarAngle = this.controls.maxPolarAngle = POLAR;
    this.controls.minZoom = 0.55;
    this.controls.maxZoom = 3.5;
    this.controls.zoomToCursor = true;
    this.controls.mouseButtons = { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE };
    this.controls.touches = { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE };
    this.controls.addEventListener("start", () => {
      this.follow = false;
      this.panGoal = null;
      this.zoomGoal = null;
    });
    this.placeCamera(new THREE.Vector3(), HOME_AZIMUTH);
    this.buildWorld();
    this.resize();
    window.addEventListener("resize", () => this.resize());

    const el = this.renderer.domElement;
    let down: { x: number; y: number } | null = null;
    el.addEventListener("pointerdown", (e) => (down = { x: e.clientX, y: e.clientY }));
    el.addEventListener("pointerup", (e) => {
      if (e.button !== 0 || !down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 5) return;
      onPick(this.pick(e));
    });
    el.addEventListener("pointermove", (e) => {
      if (e.buttons) return;
      container.classList.toggle("hover", this.pick(e) !== null);
    });
    el.addEventListener("contextmenu", (e) => e.preventDefault());
  }

  private placeCamera(target: THREE.Vector3, azimuth: number): void {
    const d = 60;
    this.controls.target.copy(target);
    this.camera.position.set(
      target.x + d * Math.sin(POLAR) * Math.sin(azimuth),
      target.y + d * Math.cos(POLAR),
      target.z + d * Math.sin(POLAR) * Math.cos(azimuth),
    );
    this.camera.lookAt(target);
  }

  private resize(): void {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.renderer.setSize(w, h);
    const view = 17.5;
    const aspect = w / Math.max(h, 1);
    Object.assign(this.camera, { left: -view * aspect, right: view * aspect, top: view, bottom: -view });
    this.camera.updateProjectionMatrix();
  }

  private buildWorld(): void {
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0xc9d3df, 2.0));
    const sun = new THREE.DirectionalLight(0xffffff, 1.9);
    sun.position.set(-14, 30, 12);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.bias = -0.0004;
    sun.shadow.normalBias = 0.04;
    sun.shadow.radius = 5;
    Object.assign(sun.shadow.camera, { left: -26, right: 26, top: 26, bottom: -26, near: 1, far: 90 });
    this.scene.add(sun);

    const mat = (color: number, roughness = 0.9) => new THREE.MeshStandardMaterial({ color, roughness });
    const box = (w: number, h: number, d: number, m: THREE.Material) => {
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
      mesh.castShadow = mesh.receiveShadow = true;
      return mesh;
    };
    const disc = (r: number, color: number, y: number) => {
      const mesh = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 0.04, 40), mat(color));
      mesh.position.y = y;
      mesh.receiveShadow = true;
      return mesh;
    };

    // ground slab with a darker rim
    const slab = box(46, 0.8, 46, mat(C.edge));
    slab.position.y = -0.42;
    const top = new THREE.Mesh(new THREE.PlaneGeometry(45.2, 45.2), mat(C.ground));
    top.rotation.x = -Math.PI / 2;
    top.position.y = -0.01;
    top.receiveShadow = true;
    this.scene.add(slab, top);

    // central plaza and roads out to each zone
    const plaza = disc(2.6, C.grass, 0.02);
    const plazaRing = disc(3.3, C.road, 0.015);
    this.scene.add(plazaRing, plaza);
    const roadMat = mat(C.road);
    const lineMat = mat(C.line);
    for (const z of Object.values(ZONES)) {
      const [x, zz] = z.pos;
      const len = Math.hypot(x, zz);
      const road = new THREE.Group();
      const strip = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.03, len), roadMat);
      strip.receiveShadow = true;
      road.add(strip);
      for (let s = -len / 2 + 0.8; s < len / 2 - 0.4; s += 1.2) {
        const dash = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.035, 0.5), lineMat);
        dash.position.z = s;
        road.add(dash);
      }
      road.position.set(x / 2, 0.01, zz / 2);
      road.rotation.y = Math.atan2(x, zz);
      this.scene.add(road);
    }

    for (const [key, z] of Object.entries(ZONES)) {
      const [x, zz] = z.pos;
      const r = Math.hypot(x, zz);
      const ux = x / r;
      const uz = zz / r;
      const bx = x + ux * BUILDING_OUT;
      const bz = zz + uz * BUILDING_OUT;
      const lawn = disc(5, C.grass, 0.012);
      lawn.position.set(x + ux * 1.6, lawn.position.y, zz + uz * 1.6);
      const pad = disc(2.9, C.pad, 0.03);
      pad.position.set(x, pad.position.y, zz);
      this.scene.add(lawn, pad);

      // building faces the plaza (local +z points to the centre)
      const b = new THREE.Group();
      const roofColor = new THREE.Color(z.color);
      const w = key === "teaching" || key === "research" ? 4.2 : 3.4;
      const h = key === "admin" ? 2.6 : 2.0;
      const walls = box(w, h, 2.6, mat(C.wall, 0.7));
      walls.position.y = h / 2;
      const roof = box(w + 0.3, 0.28, 2.9, mat(roofColor.getHex(), 0.6));
      roof.position.y = h + 0.14;
      const ridge = box(w + 0.3, 0.18, 0.5, mat(roofColor.clone().multiplyScalar(0.82).getHex(), 0.6));
      ridge.position.y = h + 0.37;
      const door = box(1.0, 1.3, 0.08, mat(roofColor.getHex(), 0.5));
      door.position.set(0, 0.65, 1.32);
      const win = box(w - 0.8, 0.42, 0.06, mat(C.window, 0.3));
      win.position.set(0, h - 0.55, 1.32);
      const sign = box(1.6, 0.36, 0.06, mat(roofColor.getHex(), 0.5));
      sign.position.set(0, h - 0.05, 1.34);
      b.add(walls, roof, ridge, door, win, sign);
      b.position.set(bx, 0, bz);
      b.rotation.y = Math.atan2(-ux, -uz);
      this.scene.add(b);

      const label = textSprite(`${z.icon} ${z.label}`, { size: 26, bg: "#ffffff", fg: "#0f1a2e" });
      label.position.set(bx, h + 1.6, bz);
      label.userData.zone = key;
      this.scene.add(label);
    }

    // trees: deterministic scatter, kept off roads, zones and the plaza
    const roadDist = (px: number, pz: number) =>
      Math.min(
        ...Object.values(ZONES).map(({ pos: [x, z] }) => {
          const u = Math.max(0, Math.min(1, (px * x + pz * z) / (x * x + z * z)));
          return Math.hypot(px - u * x, pz - u * z);
        }),
      );
    const trunkMat = mat(C.trunk);
    const leafMats = C.leaf.map((c) => mat(c, 0.8));
    for (let i = 0, placed = 0; i < 400 && placed < 48; i++) {
      const px = (hash(`tx${i}`) - 0.5) * 42;
      const pz = (hash(`tz${i}`) - 0.5) * 42;
      if (Math.hypot(px, pz) < 6 || roadDist(px, pz) < 1.6) continue;
      if (Object.values(ZONES).some(({ pos: [x, z] }) => {
        const r = Math.hypot(x, z);
        return Math.hypot(px - x * (1 + BUILDING_OUT / r * 0.6), pz - z * (1 + BUILDING_OUT / r * 0.6)) < 5.4;
      })) continue;
      const s = 0.7 + hash(`ts${i}`) * 0.6;
      const tree = new THREE.Group();
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.16, 0.9, 8), trunkMat);
      trunk.position.y = 0.45;
      const crown = new THREE.Mesh(new THREE.SphereGeometry(0.75, 16, 12), leafMats[i % leafMats.length]);
      crown.position.y = 1.45;
      crown.scale.set(1, 1.2, 1);
      for (const m of [trunk, crown]) m.castShadow = true;
      tree.add(trunk, crown);
      tree.position.set(px, 0, pz);
      tree.scale.setScalar(s);
      this.scene.add(tree);
      placed++;
    }
  }

  setRun(run: Run): void {
    this.run = run;
    for (const c of this.chars.values()) this.scene.remove(c.group);
    this.chars.clear();
    for (const t of this.trails.values()) this.scene.remove(t);
    this.trails.clear();
    this.clearCues();
    for (const a of run.agents.values()) this.chars.set(a.id, this.makeCharacter(a));
  }

  private makeCharacter(a: Agent): Character {
    const base = new THREE.Color(ARCHETYPE_COLORS[a.archetype ?? "none"] ?? ARCHETYPE_COLORS.none);
    const body = new THREE.MeshStandardMaterial({ color: base.clone(), roughness: 0.55, transparent: true });
    const head = new THREE.MeshStandardMaterial({ color: 0xf6d5b8, roughness: 0.7, transparent: true });
    const group = new THREE.Group();
    const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.32, 0.5, 4, 12), body);
    torso.position.y = 0.6;
    torso.castShadow = true;
    const skull = new THREE.Mesh(new THREE.SphereGeometry(0.27, 16, 12), head);
    skull.position.y = 1.32;
    skull.castShadow = true;
    for (const m of [torso, skull]) m.userData.agentId = a.id;
    const badge = new THREE.Group();
    badge.position.y = 1.72;
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(0.7, 0.07, 8, 32),
      new THREE.MeshBasicMaterial({ color: SELECT_COLOR }),
    );
    ring.rotation.x = Math.PI / 2;
    ring.position.y = 0.06;
    ring.visible = false;
    const label = textSprite(a.id, NAME_STYLE);
    label.position.y = 2.3;
    group.add(torso, skull, badge, ring, label);
    group.scale.setScalar(1.5);
    group.visible = false;
    this.scene.add(group);
    return { group, body, head, badge, ring, label, labelText: a.id, base, rankShown: -1 };
  }

  private setBadge(c: Character, rankIndex: number): void {
    if (c.rankShown === rankIndex) return;
    c.badge.clear();
    for (let i = 0; i <= rankIndex; i++) {
      const coin = new THREE.Mesh(
        new THREE.CylinderGeometry(0.16, 0.16, 0.07, 12),
        new THREE.MeshStandardMaterial({ color: 0xfbbf24, metalness: 0.5, roughness: 0.35 }),
      );
      coin.position.y = i * 0.1;
      c.badge.add(coin);
    }
    c.rankShown = rankIndex;
  }

  /** World position of an agent at semester t, fraction tau in [0, 1). */
  position(agent: Agent, t: number, tau: number): THREE.Vector3 {
    const s = semAt(agent, t);
    const jitterA = hash(agent.id) * Math.PI * 2;
    const jitterR = 0.6 + hash(agent.id + "r") * 1.4;
    const at = (zone: string) => {
      const [x, z] = ZONES[zone]?.pos ?? [0, 0];
      return new THREE.Vector3(x + Math.cos(jitterA) * jitterR, 0, z + Math.sin(jitterA) * jitterR);
    };
    if (!s || s.t !== t) return at("rest");
    const total = ORDER.reduce((x, k) => x + (s.hours[k] ?? 0), 0) || 1;
    let start = 0;
    let prev = "rest";
    for (const k of ORDER) {
      const d = (s.hours[k] ?? 0) / total;
      if (d <= 1e-6) continue;
      if (tau < start + d || k === ORDER[ORDER.length - 1]) {
        const u = Math.min(1, (tau - start) / d);
        const from = at(prev);
        const to = at(k);
        if (u < WALK) {
          const w = u / WALK;
          return from.lerp(to, w * w * (3 - 2 * w));
        }
        const wob = (u - WALK) * 6 + hash(agent.id + k) * 6;
        return to.add(new THREE.Vector3(Math.sin(wob) * 0.25, 0, Math.cos(wob * 0.7) * 0.25));
      }
      start += d;
      prev = k;
    }
    return at("rest");
  }

  /** Current activity zone for HUD display. */
  zoneAt(agent: Agent, t: number, tau: number): string {
    const s = semAt(agent, t);
    if (!s || s.t !== t) return "away";
    const total = ORDER.reduce((x, k) => x + (s.hours[k] ?? 0), 0) || 1;
    let start = 0;
    for (const k of ORDER) {
      const d = (s.hours[k] ?? 0) / total;
      if (tau < start + d) return k;
      start += d;
    }
    return "rest";
  }

  update(t: number, tau: number, focus: Focus): void {
    const run = this.run;
    if (!run) return;
    const ranks = run.info.rank_names;
    const focused = new Set([focus.selected, ...focus.pinned].filter(Boolean) as string[]);
    if (focus.selected !== this.lastSelected) {
      this.lastSelected = focus.selected;
      this.follow = !!focus.selected;
      if (focus.selected && this.camera.zoom < 1.35) this.zoomGoal = 1.6;
    }
    for (const a of run.agents.values()) {
      const c = this.chars.get(a.id)!;
      const present = isPresent(a, t);
      c.group.visible = present;
      if (!present) continue;
      c.group.position.copy(this.position(a, t, tau));
      const s = semAt(a, t);
      // rank shown during the semester is the rank held (promotion appears at its end)
      const paid = s && s.t === t ? s.paidRank : s?.rank;
      this.setBadge(c, Math.max(0, ranks.indexOf(paid ?? ranks[0])));
      const burnout = s?.burnout ?? 0;
      c.body.color.copy(c.base).lerp(new THREE.Color(0xb8c2cf), Math.min(1, burnout * 1.2));
      const dim = focused.size > 0 && !focused.has(a.id);
      c.body.opacity = c.head.opacity = dim ? 0.25 : 1;
      c.label.material.opacity = dim ? 0.2 : 1;
      // crowded runs: only focused lecturers keep a name tag (click or search to identify)
      c.label.visible = run.agents.size <= CROWD || focused.has(a.id);
      const selected = a.id === focus.selected;
      const text = selected ? `${a.id} · ${ZONES[this.zoneAt(a, t, tau)]?.label ?? "away"}` : a.id;
      if (text !== c.labelText) {
        setSpriteText(c.label, text, selected ? NAME_SELECTED : NAME_STYLE);
        c.labelText = text;
      }
      const pin = focus.pinned.indexOf(a.id);
      c.ring.visible = selected || pin >= 0;
      (c.ring.material as THREE.MeshBasicMaterial).color.set(selected ? SELECT_COLOR : PIN_COLORS[pin] ?? SELECT_COLOR);
    }
    this.updateCues(run, t, tau, focus);
    this.updateTrails(run, t, tau, focus);
    if (this.follow && focus.selected) {
      const a = run.agents.get(focus.selected);
      if (a && isPresent(a, t)) this.panGoal = this.position(a, t, tau);
    }
  }

  /** Camera buttons: zoom, rotate 45°, reset. */
  command(cmd: CameraCommand): void {
    const z = this.zoomGoal ?? this.camera.zoom;
    if (cmd === "in") this.zoomGoal = Math.min(this.controls.maxZoom, z * 1.3);
    if (cmd === "out") this.zoomGoal = Math.max(this.controls.minZoom, z / 1.3);
    if (cmd === "left") this.rotLeft -= Math.PI / 4;
    if (cmd === "right") this.rotLeft += Math.PI / 4;
    if (cmd === "home") {
      this.follow = false;
      this.zoomGoal = 1;
      this.panGoal = new THREE.Vector3();
      const off = this.camera.position.clone().sub(this.controls.target);
      const az = Math.atan2(off.x, off.z);
      this.rotLeft = Math.atan2(Math.sin(HOME_AZIMUTH - az), Math.cos(HOME_AZIMUTH - az));
    }
  }

  private animateCamera(): void {
    const k = 0.15;
    if (this.zoomGoal !== null) {
      const dz = this.zoomGoal - this.camera.zoom;
      this.camera.zoom = Math.abs(dz) < 1e-3 ? this.zoomGoal : this.camera.zoom + dz * k;
      if (this.camera.zoom === this.zoomGoal) this.zoomGoal = null;
      this.camera.updateProjectionMatrix();
    }
    if (Math.abs(this.rotLeft) > 1e-4) {
      const step = Math.abs(this.rotLeft) < 1e-3 ? this.rotLeft : this.rotLeft * k;
      const off = this.camera.position.clone().sub(this.controls.target);
      off.applyAxisAngle(new THREE.Vector3(0, 1, 0), step);
      this.camera.position.copy(this.controls.target).add(off);
      this.rotLeft -= step;
    }
    const target = this.controls.target;
    if (this.panGoal) {
      const delta = this.panGoal.clone().sub(target).setY(0);
      if (!this.follow && delta.length() < 0.01) this.panGoal = null;
      delta.multiplyScalar(this.follow ? 0.08 : k);
      target.add(delta);
      this.camera.position.add(delta);
    }
    const clamp = new THREE.Vector3(
      Math.max(-MAP_LIMIT, Math.min(MAP_LIMIT, target.x)) - target.x,
      0,
      Math.max(-MAP_LIMIT, Math.min(MAP_LIMIT, target.z)) - target.z,
    );
    target.add(clamp);
    this.camera.position.add(clamp);
  }

  private clearCues(): void {
    for (const c of this.cues) this.scene.remove(c.sprite);
    this.cues = [];
    this.cueKey = "";
  }

  private updateCues(run: Run, t: number, tau: number, focus: Focus): void {
    const key = `${t}|${focus.selected}`;
    if (key !== this.cueKey) {
      this.clearCues();
      this.cueKey = key;
      // Group by agent and kind: the focused agent gets full text, others a compact icon
      // with a count, so busy semesters stay readable.
      const groups = new Map<string, KeyEvent[]>();
      for (const ev of run.events.get(t) ?? []) {
        const mine = ev.agent === focus.selected;
        if (ev.kind === "teaching" && ev.outcome === "accepted" && !mine) continue;
        if (ev.kind === "coauthor" && !mine) continue;
        if (ev.kind !== "teaching" && !CUE_ICONS[ev.kind]) continue;
        const k = `${ev.agent}|${ev.kind}|${ev.outcome ?? ""}`;
        if (!groups.has(k)) groups.set(k, []);
        groups.get(k)!.push(ev);
      }
      const perAgent = new Map<string, number>();
      for (const evs of groups.values()) {
        const ev = evs[0];
        const mine = ev.agent === focus.selected;
        const icon = ev.kind === "teaching" ? "💬" : CUE_ICONS[ev.kind]!;
        const text = mine
          ? `${icon} ${ev.text}${evs.length > 1 ? ` ×${evs.length}` : ""}`
          : `${icon}${evs.length > 1 ? ` ×${evs.length}` : ""}${ev.outcome === "imposed" ? " imposed" : ""}`;
        const n = perAgent.get(ev.agent) ?? 0;
        perAgent.set(ev.agent, n + 1);
        const style: PillStyle = ev.outcome === "imposed"
          ? { size: mine ? 24 : 20, bg: "#fdecec", fg: "#dc2626", border: "#f5b5b5" }
          : ev.kind === "promotion"
            ? { size: mine ? 24 : 20, bg: "#fff4e2", fg: "#b45309", border: "#f8d79b" }
            : { size: mine ? 24 : 20, bg: "#ffffff", fg: "#0f1a2e", border: "#e7ecf3" };
        const sprite = textSprite(text, style);
        this.scene.add(sprite);
        this.cues.push({ sprite, agent: ev.agent, offset: n });
      }
    }
    for (const c of this.cues) {
      const a = run.agents.get(c.agent);
      const visible = !!a && tau < CUE_LIFE;
      c.sprite.visible = visible;
      if (!visible || !a) continue;
      const p = this.position(a, t, tau);
      c.sprite.position.set(p.x, 4.6 + c.offset * 0.9 + tau * 2, p.z);
      c.sprite.material.opacity = 1 - tau / CUE_LIFE;
    }
  }

  private updateTrails(run: Run, t: number, tau: number, focus: Focus): void {
    const want = focus.trail ? [focus.selected, ...focus.pinned].filter(Boolean) as string[] : [];
    for (const [id, line] of this.trails) {
      if (!want.includes(id)) {
        this.scene.remove(line);
        this.trails.delete(id);
      }
    }
    for (const id of want) {
      const a = run.agents.get(id);
      if (!a || !isPresent(a, t)) continue;
      const pts: THREE.Vector3[] = [];
      const steps = 80;
      for (let i = 0; i <= steps; i++) {
        const u = (tau * i) / steps;
        pts.push(this.position(a, t, u).setY(0.08));
      }
      let line = this.trails.get(id);
      const color = id === focus.selected ? SELECT_COLOR : PIN_COLORS[focus.pinned.indexOf(id)] ?? SELECT_COLOR;
      if (!line) {
        line = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color }));
        this.trails.set(id, line);
        this.scene.add(line);
      }
      (line.material as THREE.LineBasicMaterial).color.set(color);
      line.geometry.setFromPoints(pts);
    }
  }

  private pick(e: PointerEvent): string | null {
    const rect = this.renderer.domElement.getBoundingClientRect();
    const ndc = new THREE.Vector2(
      ((e.clientX - rect.left) / rect.width) * 2 - 1,
      -((e.clientY - rect.top) / rect.height) * 2 + 1,
    );
    this.raycaster.setFromCamera(ndc, this.camera);
    const meshes: THREE.Object3D[] = [];
    for (const c of this.chars.values()) if (c.group.visible) meshes.push(...c.group.children);
    const hit = this.raycaster.intersectObjects(meshes, false).find((h) => h.object.userData.agentId);
    return hit ? (hit.object.userData.agentId as string) : null;
  }

  render(): void {
    this.animateCamera();
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}

export const zoneColor = (k: string): string => hex(ZONES[k]?.color ?? 0x9aa7b8);
