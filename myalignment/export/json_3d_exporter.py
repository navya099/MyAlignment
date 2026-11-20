from html import escape
import json
from pathlib import Path
from string import Template

from myalignment.export.scene_3d_serializer import Scene3DSerializer
from myalignment.render.scene_3d import Scene3D


class Json3DExporter:
    """3D Scene을 JSON 또는 모델 데이터가 포함된 HTML로 저장한다."""

    @classmethod
    def export(cls, scene: Scene3D, path: str | Path, indent: int | None = 2) -> None:
        Path(path).write_text(Scene3DSerializer.to_json(scene, indent), encoding="utf-8")

    @classmethod
    def export_to_html(
        cls, scene: Scene3D, html_path: str | Path, title: str = "3D Corridor Viewer",
        *, three_module_base: str = "https://cdn.jsdelivr.net/npm/three@0.160.0/",
    ) -> None:
        """three_module_base는 CDN 또는 동일 버전의 로컬 배포 디렉터리 URL이다."""
        base = three_module_base.rstrip("/") + "/"
        import_map = json.dumps({"imports": {
            "three": base + "build/three.module.js",
            "three/addons/": base + "examples/jsm/",
        }}).replace("<", r"\u003c")
        # JSON script의 종료 태그를 사용자 데이터가 만들 수 없게 한다.
        payload = Scene3DSerializer.to_json(scene, indent=None).replace("<", r"\u003c")
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
  aside h2 { margin: 0 0 12px; font-size: 13px; color: #bfd2dc; }
  label { display: flex; align-items: start; gap: 8px; margin-bottom: 8px; overflow-wrap: anywhere; }
  input { accent-color: #80d8c9; margin: 2px 0; }
  footer { padding: 9px 20px; background: #18232c; color: #bfd2dc; border-top: 1px solid #344652; }
  #status { margin: 0; }
</style>
<script type="importmap">
$import_map
</script>
</head>
<body>
<header><h1>$title</h1><button id="fit" type="button" disabled>전체 보기</button></header>
<main><div id="viewport" aria-label="3D 코리더 모델"></div>
<aside hidden><h2>레이어</h2><div id="layers"></div></aside></main>
<footer><p id="status" role="status">모델을 불러오는 중…</p></footer>
<script type="application/json" id="scene-data">$scene_json</script>
<script type="module">
const status = document.querySelector('#status');
const viewport = document.querySelector('#viewport');
const fit = document.querySelector('#fit');
const data = JSON.parse(document.querySelector('#scene-data').textContent);
async function render() {
  if (!data.primitives.length) {
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
  const center = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());
  const radius = Math.max(size.length() / 2, 0.01);
  // CAD의 Z-up 좌표를 재중심화한다. Float32 변환 전에 큰 월드 좌표를 제거한다.
  const local = ([x, y, z]) => [x - center.x, z - center.z, center.y - y];

  const groups = new Map();
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
      scene.add(group);
    }
    const group = groups.get(prim.layer);
    if (prim.type === 'mesh') {
      const shape = geometry(prim.vertices.flatMap(local));
      shape.setIndex(prim.indices.flat());
      shape.computeVertexNormals();
      group.add(new THREE.Mesh(shape, new THREE.MeshStandardMaterial({
        color: prim.color, side: THREE.DoubleSide, roughness: .85, flatShading: true,
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
  for (const [name, group] of groups) {
    const row = document.createElement('label');
    const input = document.createElement('input');
    input.type = 'checkbox';
    input.checked = true;
    input.addEventListener('change', () => { group.visible = input.checked; });
    row.append(input, document.createTextNode(name));
    document.querySelector('#layers').append(row);
  }
  document.querySelector('aside').hidden = false;

  function resize() {
    const width = Math.max(viewport.clientWidth, 1);
    const height = Math.max(viewport.clientHeight, 1);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }
  function fitModel() {
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
  fit.addEventListener('click', fitModel);
  status.textContent = '메쉬 ' + meshCount + ' · 선 ' + lineCount + ' · 삼각형 ' + faceCount;
  renderer.setAnimationLoop(() => {
    controls.update();
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
