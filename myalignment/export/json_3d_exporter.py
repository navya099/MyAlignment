from collections.abc import Mapping, Sequence
from dataclasses import replace
from html import escape
import json
from pathlib import Path
from string import Template

from myalignment.export.scene_3d_serializer import Scene3DSerializer
from myalignment.render.primitives_3d import PrimitiveType3D
from myalignment.render.scene_3d import Scene3D


class Json3DExporter:
    """3D Scene을 JSON 또는 모델 데이터가 포함된 HTML로 저장한다."""

    @classmethod
    def export(cls, scene: Scene3D, path: str | Path, indent: int | None = 2) -> None:
        Path(path).write_text(Scene3DSerializer.to_json(scene, indent), encoding="utf-8")

    @classmethod
    def export_mesh_with_legend(
        cls, scene: Scene3D, html_path: str | Path, title: str = "3D Mesh Viewer",
        legend: Sequence[Mapping[str, str]] | None = None, *,
        three_module_base: str = "https://cdn.jsdelivr.net/npm/three@0.160.0/",
    ) -> None:
        """기존 뷰어에서 메시 레이어별 색상 또는 사용자 범례를 표시한다."""
        labels = {
            primitive.style.layer or "0": primitive.style.layer or "0"
            for primitive in scene.primitives
            if primitive.style.visible
            and (primitive.type is PrimitiveType3D.TRIANGLE
                 or (primitive.type is PrimitiveType3D.MESH and primitive.indices))
        }
        metadata = dict(scene.metadata)
        labels.update(metadata.get("mesh_layers", {}))
        metadata["mesh_layers"] = labels
        if legend is not None:
            metadata["mesh_legend"] = [{"name": item["name"], "color": item["color"]} for item in legend]
        cls.export_to_html(replace(scene, metadata=metadata), html_path, title, three_module_base=three_module_base)

    @classmethod
    def export_to_html(
        cls, scene: Scene3D, html_path: str | Path, title: str = "3D Corridor Viewer",
        *, three_module_base: str = "https://cdn.jsdelivr.net/npm/three@0.160.0/",
    ) -> None:
        """three_module_base는 CDN 또는 동일 버전의 로컬 배포 디렉터리 URL이다."""
        cls._write_html(Scene3DSerializer.to_dict(scene), html_path, title, three_module_base=three_module_base)

    @staticmethod
    def _write_html(
        data: dict, html_path: str | Path, title: str, *,
        three_module_base: str = "https://cdn.jsdelivr.net/npm/three@0.160.0/",
    ) -> None:
        base = three_module_base.rstrip("/") + "/"
        import_map = json.dumps({"imports": {
            "three": base + "build/three.module.js",
            "three/addons/": base + "examples/jsm/",
        }}).replace("<", r"\u003c")
        # JSON script의 종료 태그를 사용자 데이터가 만들 수 없게 한다.
        payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("<", r"\u003c")
        html = _HTML_TEMPLATE.substitute(title=escape(title), scene_json=payload, import_map=import_map)
        Path(html_path).write_text(html, encoding="utf-8")


_HTML_TEMPLATE = Template("""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; background: #101820; color: #ecf1f4; font: 14px system-ui, sans-serif; }
  header { display: flex; align-items: center; justify-content: space-between; gap: 16px;
           padding: 14px 20px; border-bottom: 1px solid #344652; background: #18232c; }
  h1 { font-size: 16px; font-weight: 600; margin: 0; overflow-wrap: anywhere; }
  button { background: #233742; color: inherit; border: 1px solid #496674;
           border-radius: 6px; padding: 8px 12px; white-space: nowrap; cursor: pointer; }
  button:disabled { opacity: .5; cursor: default; }
  main { position: relative; display: grid; min-height: 0; grid-template-columns: minmax(0, 1fr) auto; }
  body { height: 100vh; height: 100dvh; display: grid; grid-template-rows: auto minmax(0, 1fr) auto; }
  #viewport { min-width: 0; min-height: 0; position: relative; overflow: hidden; }
  canvas { display: block; touch-action: none; }
  aside { width: clamp(145px, 20vw, 260px); padding: 16px; background: #18232c;
          border-left: 1px solid #344652; overflow: auto; }
  aside h2, aside h3 { margin: 0 0 12px; font-size: 13px; color: #bfd2dc; }
  label { display: flex; align-items: start; gap: 8px; margin-bottom: 8px; overflow-wrap: anywhere; }
  .legend-item { display: flex; gap: 8px; margin: 8px 0; overflow-wrap: anywhere; }
  #mesh-legend { margin-top: 12px; }
  input { accent-color: #80d8c9; margin: 2px 0; }
  .swatch { width: 12px; height: 12px; flex: 0 0 12px; border-radius: 2px; margin-top: 2px; }
  footer { padding: 9px 20px; background: #18232c; color: #bfd2dc; border-top: 1px solid #344652; }
  #status { margin: 0; }
  #drive-controls:not([hidden]) { display: flex; align-items: center; flex-wrap: wrap; gap: 10px 14px; }
  #drive-controls label { align-items: center; margin: 0; }
  #drive-time { flex: 1 1 180px; min-width: 100px; }
  #drive-readout { font-variant-numeric: tabular-nums; }
</style>
<script type="importmap">
$import_map
</script>
</head>
<body>
<header><h1>$title</h1><button id="fit" type="button" disabled>전체 보기</button></header>
<main><div id="viewport" aria-label="3D 코리더 모델"></div>
<aside hidden><h2>레이어</h2><div id="layers"></div>
<section id="mesh-legend" hidden><h3>메시 범례</h3><div id="mesh-legend-items"></div></section>
</aside></main>
<footer>
<p id="status" role="status">모델을 불러오는 중…</p>
<section id="drive-controls" aria-label="주행 제어" hidden>
<button id="drive-play" type="button">재생</button>
<button id="drive-reset" type="button">처음으로</button>
<input id="drive-time" type="range" min="0" step="any" value="0" aria-label="재생 시각">
<label>재생 속도 <select id="drive-speed">
<option value="0.25">0.25×</option><option value="0.5">0.5×</option><option value="1" selected>1×</option>
<option value="2">2×</option><option value="4">4×</option>
</select></label>
<span id="drive-readout"></span>
</section>
</footer>
<script type="application/json" id="scene-data">$scene_json</script>
<script type="module">
const status = document.querySelector('#status');
const viewport = document.querySelector('#viewport');
const fit = document.querySelector('#fit');
const data = JSON.parse(document.querySelector('#scene-data').textContent);
function setupDrive(THREE, drive, camera, controls, canvas, local) {
  const frames = drive.frames;
  const duration = drive.duration;
  const ui = document.querySelector('#drive-controls');
  const play = document.querySelector('#drive-play');
  const reset = document.querySelector('#drive-reset');
  const seek = document.querySelector('#drive-time');
  const speed = document.querySelector('#drive-speed');
  const readout = document.querySelector('#drive-readout');
  let time = 0, playing = false, active = false, previous = null;
  let yaw = 0, pitch = 0;

  function frameAt(t) {
    let lo = 0, hi = frames.length;
    while (lo < hi) {
      const mid = Math.floor((lo + hi) / 2);
      if (frames[mid].timestamp < t) lo = mid + 1;
      else hi = mid;
    }
    const b = frames[Math.min(lo, frames.length - 1)];
    if (lo === 0 || lo === frames.length || b.timestamp === t) return b;
    const a = frames[lo - 1];
    const f = (t - a.timestamp) / (b.timestamp - a.timestamp);
    const mix = (x, y) => x + (y - x) * f;
    const vector = (x, y) => x.map((value, axis) => mix(value, y[axis]));
    return {
      position: vector(a.position, b.position), target: vector(a.target, b.target),
      up: vector(a.up, b.up), fov: mix(a.fov, b.fov), station: mix(a.station, b.station),
    };
  }

  function draw() {
    const frame = frameAt(time);
    camera.position.set(...local(frame.position));
    const [x, y, z] = frame.up;
    camera.up.set(x, z, -y);
    if (camera.up.lengthSq() < 1e-12) camera.up.set(0, 1, 0);
    const target = new THREE.Vector3(...local(frame.target));
    if (target.distanceToSquared(camera.position) < 1e-12) target.x += 1;
    camera.lookAt(target);
    camera.rotateY(yaw);
    camera.rotateX(pitch);
    camera.fov = frame.fov;
    camera.near = drive.near_plane;
    camera.far = drive.far_plane;
    camera.updateProjectionMatrix();
    seek.value = time;
    const kmh = drive.speed_kmh * Number(speed.value);
    readout.textContent = 'STA ' + frame.station.toFixed(2) + ' · ' + time.toFixed(2)
      + ' / ' + duration.toFixed(2) + ' s · ' + kmh.toFixed(1) + ' km/h';
  }

  function setPlaying(value) {
    playing = value;
    previous = null;
    play.textContent = value ? '일시정지' : '재생';
  }

  function enter() {
    active = true;
    controls.enabled = false;
    draw();
  }

  play.addEventListener('click', () => {
    enter();
    if (!playing && time >= duration) time = 0;
    setPlaying(!playing);
    draw();
  });
  reset.addEventListener('click', () => {
    time = yaw = pitch = 0;
    setPlaying(false);
    enter();
  });
  seek.addEventListener('input', () => {
    time = Number(seek.value);
    setPlaying(false);
    enter();
  });
  speed.addEventListener('change', () => { if (active) draw(); });
  if (drive.direction_mode === 'Free') {
    canvas.addEventListener('pointermove', event => {
      if (!active || !(event.buttons & 1)) return;
      yaw -= event.movementX * .003;
      pitch = Math.max(-1.5, Math.min(1.5, pitch - event.movementY * .003));
      draw();
    });
  }
  seek.max = duration;
  seek.disabled = play.disabled = duration === 0;
  ui.hidden = false;
  enter();

  return {
    overview() {
      active = false;
      controls.enabled = true;
      camera.up.set(0, 1, 0);
      setPlaying(false);
    },
    tick(now) {
      if (playing) {
        if (previous !== null) time = Math.min(duration, time + (now - previous) / 1000 * Number(speed.value));
        previous = now;
        if (time >= duration) setPlaying(false);
        draw();
      }
      return active;
    },
  };
}

async function render() {
  const drive = data.metadata?.drive_view;
  if (!data.primitives.length && !drive?.frames?.length) {
    status.textContent = '표시할 3D 도형이 없습니다.';
    return;
  }
  const [THREE, {OrbitControls}] = await Promise.all([
    import('three'), import('three/addons/controls/OrbitControls.js')
  ]);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#101820');
  const camera = new THREE.PerspectiveCamera(50);
  const renderer = new THREE.WebGLRenderer({antialias: true});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  viewport.appendChild(renderer.domElement);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  const bounds = new THREE.Box3();
  function vertices(prim) {
    if (prim.type === 'mesh') return prim.vertices;
    if (prim.type === 'polyline') return prim.points;
    if (prim.type === 'point') return [prim.position];
    return [prim.start, prim.end];
  }
  for (const prim of data.primitives) {
    for (const point of vertices(prim)) bounds.expandByPoint(new THREE.Vector3(...point));
  }
  for (const frame of drive?.frames ?? []) bounds.expandByPoint(new THREE.Vector3(...frame.position));
  const center = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());
  const radius = Math.max(size.length() / 2, 0.01);
  // CAD의 Z-up 좌표를 재중심화한다. Float32 변환 전에 큰 월드 좌표를 제거한다.
  const local = ([x, y, z]) => [x - center.x, z - center.z, center.y - y];

  const groups = new Map();
  const colors = new Map();
  const lines = new Map();
  const points = new Map();
  function geometry(positions) {
    return new THREE.BufferGeometry().setAttribute(
      'position', new THREE.Float32BufferAttribute(positions, 3)
    );
  }
  let meshCount = 0, faceCount = 0, lineCount = 0;
  for (const prim of data.primitives) {
    if (!groups.has(prim.layer)) {
      const group = new THREE.Group();
      groups.set(prim.layer, group);
      colors.set(prim.layer, prim.color);
      scene.add(group);
    }
    const group = groups.get(prim.layer);
    if (prim.type === 'mesh') {
      const shape = geometry(prim.vertices.flatMap(local));
      shape.setIndex(prim.indices.flat());
      shape.computeVertexNormals();
      const opacity = prim.opacity ?? 1;
      group.add(new THREE.Mesh(shape, new THREE.MeshStandardMaterial({
        color: prim.color, side: THREE.DoubleSide, roughness: .85, flatShading: true,
        opacity, transparent: opacity < 1, depthWrite: opacity === 1,
        polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1
      })));
      meshCount++;
      faceCount += prim.indices.length;
    } else {
      const batches = prim.type === 'point' ? points : lines;
      const key = JSON.stringify([prim.layer, prim.color]);
      if (!batches.has(key)) batches.set(key, {group, color: prim.color, positions: []});
      const bucket = batches.get(key);
      const path = vertices(prim).map(local);
      if (prim.type === 'point') {
        bucket.positions.push(...path[0]);
      } else {
        for (let i = 1; i < path.length; i++) {
          bucket.positions.push(...path[i - 1], ...path[i]);
        }
        if (prim.closed && path[0].some((value, axis) => value !== path.at(-1)[axis])) {
          bucket.positions.push(...path.at(-1), ...path[0]);
        }
        lineCount++;
      }
    }
  }
  for (const {group, color, positions} of lines.values()) {
    group.add(new THREE.LineSegments(geometry(positions), new THREE.LineBasicMaterial({color})));
  }
  for (const {group, color, positions} of points.values()) {
    group.add(new THREE.Points(geometry(positions), new THREE.PointsMaterial({
      color, size: 5, sizeAttenuation: false
    })));
  }

  scene.add(new THREE.HemisphereLight(0xffffff, 0x667485, 2));
  const sun = new THREE.DirectionalLight(0xffffff, 2);
  sun.position.set(1, 3, 2);
  scene.add(sun);
  function appendLegendItem(row, color, label) {
    const swatch = document.createElement('span');
    swatch.className = 'swatch';
    swatch.style.backgroundColor = color;
    row.append(swatch, document.createTextNode(label));
  }

  const meshLayers = data.metadata?.mesh_layers ?? {};
  for (const [name, group] of groups) {
    const row = document.createElement('label');
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.checked = true;
    input.addEventListener('change', () => { group.visible = input.checked; });
    row.append(input);
    const entry = data.metadata?.link_surfaces?.[name];
    if (entry) {
      appendLegendItem(row, colors.get(name), entry.name + ' (' + entry.area_2d.toFixed(1) + ' m²)');
    } else if (Object.hasOwn(meshLayers, name)) {
      appendLegendItem(row, colors.get(name), meshLayers[name]);
    } else {
      row.append(document.createTextNode(name));
    }
    document.querySelector('#layers').append(row);
  }
  const legend = data.metadata?.mesh_legend ?? [];
  if (legend.length) {
    const items = document.querySelector('#mesh-legend-items');
    for (const {name, color} of legend) {
      const row = document.createElement('div');
      row.className = 'legend-item';
      appendLegendItem(row, color, name);
      items.append(row);
    }
    document.querySelector('#mesh-legend').hidden = false;
  }
  document.querySelector('aside').hidden = groups.size === 0;

  function resize() {
    const width = Math.max(viewport.clientWidth, 1);
    const height = Math.max(viewport.clientHeight, 1);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }
  function fitModel() {
    camera.fov = 50;
    const halfFov = THREE.MathUtils.degToRad(camera.fov / 2);
    const angle = Math.min(halfFov, Math.atan(Math.tan(halfFov) * camera.aspect));
    const distance = radius / Math.sin(angle) * 1.15;
    camera.near = Math.max(radius / 10000, distance / 100000);
    camera.far = distance + radius * 100;
    camera.updateProjectionMatrix();
    camera.position.set(1, .8, 1).normalize().multiplyScalar(distance);
    controls.target.set(0, 0, 0);
    controls.update();
  }

  new ResizeObserver(resize).observe(viewport);
  resize();
  fitModel();
  fit.disabled = false;
  const driver = drive?.frames?.length ? setupDrive(THREE, drive, camera, controls, renderer.domElement, local) : null;
  fit.addEventListener('click', () => {
    driver?.overview();
    fitModel();
  });
  status.textContent = '메쉬 ' + meshCount + ' · 선 ' + lineCount + ' · 삼각형 ' + faceCount;
  renderer.setAnimationLoop(now => {
    if (!driver?.tick(now)) controls.update();
    renderer.render(scene, camera);
  });
}
render().catch(error => {
  console.error(error);
  status.textContent = '3D 미리보기를 열 수 없습니다. WebGL과 인터넷 연결을 확인하세요.';
});
</script>
</body>
</html>
""")
