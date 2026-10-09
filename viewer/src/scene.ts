// Three.js campus: one zone per activity; characters walk between zones in proportion to
// their logged weekly hours. Animation is a pure function of (semester, tau) so scrubbing
// is deterministic and never touches simulation data.

import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { type Agent, type KeyEvent, type Run, isPresent, semAt } from "./log";

export const ZONES: Record<string, { label: string; icon: string; color: number; pos: [number, number] }> = {
  teaching: { label: "Lecture hall", icon: "🎓", color: 0x4c6ef5, pos: [-8, -6] },
  research: { label: "Lab", icon: "🔬", color: 0x12b886, pos: [0, -9] },
  supervision: { label: "Supervision room", icon: "🧑‍🏫", color: 0x15aabf, pos: [8, -6] },
  community_service: { label: "Village hall", icon: "🏘️", color: 0x82c91e, pos: [-10, 3] },
  admin: { label: "Admin building", icon: "🗂️", color: 0x868e96, pos: [10, 3] },
  external: { label: "Consulting office", icon: "💼", color: 0xf59f00, pos: [5, 10] },
  rest: { label: "Café / home", icon: "☕", color: 0xe64980, pos: [-5, 10] },
};
const ORDER = ["teaching", "research", "supervision", "community_service", "admin", "external", "rest"];

export const ARCHETYPE_COLORS: Record<string, string> = {
  research_maximiser: "#20c997",
  teaching_loyalist: "#5c7cfa",
  admin_climber: "#adb5bd",
  external_earner: "#fcc419",
  balanced_strategist: "#f06595",
  none: "#e8590c",
};
export const PIN_COLORS = ["#ff4d6d", "#4dabf7", "#ffd43b"];

const CUE_ICONS: Partial<Record<KeyEvent["kind"], string>> = {
  paper: "📄",
  promotion: "⭐",
  grant: "💰",
  role: "🏷️",
  coauthor: "🤝",
  attrition: "🚪",
  hire: "👋",
  certified: "📜",
};
const WALK = 0.18; // fraction of each segment spent walking
const CUE_LIFE = 0.45; // cues fade over this fraction of a semester

function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return (h >>> 0) / 4294967296;
}

function textSprite(text: string, opts: { size?: number; bg?: string; fg?: string } = {}): THREE.Sprite {
  const size = opts.size ?? 28;
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d")!;
  ctx.font = `600 ${size}px system-ui, sans-serif`;
  const w = Math.ceil(ctx.measureText(text).width) + 20;
  canvas.width = w;
  canvas.height = size + 16;
  ctx.font = `600 ${size}px system-ui, sans-serif`;
  if (opts.bg) {
    ctx.fillStyle = opts.bg;
    ctx.beginPath();
    ctx.roundRect(0, 0, w, size + 16, 10);
    ctx.fill();
  }
  ctx.fillStyle = opts.fg ?? "#f8f9fa";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 10, (size + 16) / 2);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  const scale = 0.022;
  sprite.scale.set(w * scale, (size + 16) * scale, 1);
  sprite.renderOrder = 10;
  return sprite;
}

interface Character {
  group: THREE.Group;
  body: THREE.MeshStandardMaterial;
  head: THREE.MeshStandardMaterial;
  badge: THREE.Group;
  ring: THREE.Mesh;
  label: THREE.Sprite;
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

  constructor(private container: HTMLElement, onPick: (id: string | null) => void) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    container.appendChild(this.renderer.domElement);
    this.scene.background = new THREE.Color(0x1b1f2a);
    this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 500);
    this.camera.position.set(28, 30, 28);
    this.camera.zoom = 1;
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.maxPolarAngle = Math.PI / 2.3;
    this.buildWorld();
    this.resize();
    window.addEventListener("resize", () => this.resize());

    let down: { x: number; y: number } | null = null;
    this.renderer.domElement.addEventListener("pointerdown", (e) => (down = { x: e.clientX, y: e.clientY }));
    this.renderer.domElement.addEventListener("pointerup", (e) => {
      if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 5) return;
      onPick(this.pick(e));
    });
  }

  private resize(): void {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.renderer.setSize(w, h);
    const view = 14;
    const aspect = w / Math.max(h, 1);
    Object.assign(this.camera, { left: -view * aspect, right: view * aspect, top: view, bottom: -view });
    this.camera.updateProjectionMatrix();
  }

  private buildWorld(): void {
    this.scene.add(new THREE.HemisphereLight(0xdde6ff, 0x30343f, 1.6));
    const sun = new THREE.DirectionalLight(0xffffff, 1.6);
    sun.position.set(15, 30, 10);
    sun.castShadow = true;
    sun.shadow.camera.left = sun.shadow.camera.bottom = -25;
    sun.shadow.camera.right = sun.shadow.camera.top = 25;
    this.scene.add(sun);
    const ground = new THREE.Mesh(
      new THREE.CylinderGeometry(19, 19, 0.6, 48),
      new THREE.MeshStandardMaterial({ color: 0x2f9e44, roughness: 1 }),
    );
    ground.position.y = -0.3;
    ground.receiveShadow = true;
    this.scene.add(ground);
    const plaza = new THREE.Mesh(
      new THREE.CylinderGeometry(4.5, 4.5, 0.05, 32),
      new THREE.MeshStandardMaterial({ color: 0xced4da, roughness: 1 }),
    );
    plaza.position.y = 0.02;
    this.scene.add(plaza);
    for (const [key, z] of Object.entries(ZONES)) {
      const [x, zz] = z.pos;
      const pad = new THREE.Mesh(
        new THREE.CylinderGeometry(3.1, 3.1, 0.08, 28),
        new THREE.MeshStandardMaterial({ color: 0xe9ecef, roughness: 1 }),
      );
      pad.position.set(x, 0.04, zz);
      pad.receiveShadow = true;
      const bx = Math.sign(x || 1) * 1.6;
      const bz = Math.sign(zz || 1) * 1.6;
      const house = new THREE.Mesh(
        new THREE.BoxGeometry(2.2, 1.8, 2.2),
        new THREE.MeshStandardMaterial({ color: z.color, roughness: 0.7 }),
      );
      house.position.set(x + bx, 0.9, zz + bz);
      house.castShadow = true;
      const roof = new THREE.Mesh(
        new THREE.ConeGeometry(1.8, 1.1, 4),
        new THREE.MeshStandardMaterial({ color: 0x343a40, roughness: 0.8 }),
      );
      roof.position.set(x + bx, 2.35, zz + bz);
      roof.rotation.y = Math.PI / 4;
      roof.castShadow = true;
      const label = textSprite(`${z.icon} ${z.label}`, { size: 30, bg: "rgba(20,24,33,0.75)" });
      label.position.set(x + bx, 3.5, zz + bz);
      label.userData.zone = key;
      this.scene.add(pad, house, roof, label);
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
    const base = new THREE.Color(ARCHETYPE_COLORS[a.archetype ?? "none"] ?? "#e8590c");
    const body = new THREE.MeshStandardMaterial({ color: base.clone(), roughness: 0.6, transparent: true });
    const head = new THREE.MeshStandardMaterial({ color: 0xffe0bd, roughness: 0.7, transparent: true });
    const group = new THREE.Group();
    const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.38, 0.95, 12), body);
    torso.position.y = 0.48;
    torso.castShadow = true;
    const skull = new THREE.Mesh(new THREE.SphereGeometry(0.27, 16, 12), head);
    skull.position.y = 1.18;
    skull.castShadow = true;
    for (const m of [torso, skull]) m.userData.agentId = a.id;
    const badge = new THREE.Group();
    badge.position.y = 1.6;
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(0.7, 0.07, 8, 32),
      new THREE.MeshBasicMaterial({ color: 0xffffff }),
    );
    ring.rotation.x = Math.PI / 2;
    ring.position.y = 0.06;
    ring.visible = false;
    const label = textSprite(a.id, { size: 22, bg: "rgba(0,0,0,0.55)" });
    label.position.y = 2.25;
    group.add(torso, skull, badge, ring, label);
    group.scale.setScalar(1.6);
    group.visible = false;
    this.scene.add(group);
    return { group, body, head, badge, ring, label, base, rankShown: -1 };
  }

  private setBadge(c: Character, rankIndex: number): void {
    if (c.rankShown === rankIndex) return;
    c.badge.clear();
    for (let i = 0; i <= rankIndex; i++) {
      const disc = new THREE.Mesh(
        new THREE.CylinderGeometry(0.16, 0.16, 0.07, 12),
        new THREE.MeshStandardMaterial({ color: 0xffd43b, metalness: 0.6, roughness: 0.3 }),
      );
      disc.position.y = i * 0.1;
      c.badge.add(disc);
    }
    c.rankShown = rankIndex;
  }

  /** World position of an agent at semester t, fraction tau in [0, 1). */
  position(agent: Agent, t: number, tau: number): THREE.Vector3 {
    const s = semAt(agent, t);
    const jitterA = hash(agent.id) * Math.PI * 2;
    const jitterR = 0.8 + hash(agent.id + "r") * 1.6;
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
      c.body.color.copy(c.base).lerp(new THREE.Color(0x495057), Math.min(1, burnout * 1.2));
      const dim = focused.size > 0 && !focused.has(a.id);
      c.body.opacity = c.head.opacity = dim ? 0.22 : 1;
      c.label.material.opacity = dim ? 0.15 : 0.95;
      const pin = focus.pinned.indexOf(a.id);
      c.ring.visible = a.id === focus.selected || pin >= 0;
      (c.ring.material as THREE.MeshBasicMaterial).color.set(
        a.id === focus.selected ? "#ffffff" : PIN_COLORS[pin] ?? "#ffffff",
      );
    }
    this.updateCues(run, t, tau, focus);
    this.updateTrails(run, t, tau, focus);
    if (focus.selected) {
      const a = run.agents.get(focus.selected);
      if (a && isPresent(a, t)) {
        const p = this.position(a, t, tau);
        const delta = p.clone().sub(this.controls.target).multiplyScalar(0.08);
        this.controls.target.add(delta);
        this.camera.position.add(delta);
      }
    }
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
          : `${icon}${evs.length > 1 ? `×${evs.length}` : ""}${ev.outcome === "imposed" ? " imposed" : ""}`;
        const n = perAgent.get(ev.agent) ?? 0;
        perAgent.set(ev.agent, n + 1);
        const bg = ev.outcome === "imposed" ? "rgba(201,42,42,0.85)" : "rgba(33,37,41,0.8)";
        const sprite = textSprite(text, { size: mine ? 26 : 22, bg });
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
      c.sprite.position.set(p.x, 4.2 + c.offset * 0.9 + tau * 2, p.z);
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
        pts.push(this.position(a, t, u).setY(0.12));
      }
      let line = this.trails.get(id);
      const color = id === focus.selected ? "#ffffff" : PIN_COLORS[focus.pinned.indexOf(id)] ?? "#fff";
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
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}
