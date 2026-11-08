/**
 * HUMANS APOCALYPSE — COMBAT LAB 0.3
 * Browser-first gameplay experiment. No library / runtime dependencies.
 * All entities use world units. All render positions use a camera transform.
 * Temporary vector actors live in renderActor; artists can supply transparent sprites.
 */
const canvas = document.querySelector('#game');
const ctx = canvas.getContext('2d', { alpha: false });
const overlay = document.querySelector('#overlay');
const panel = document.querySelector('#panel');
const actions = document.querySelector('#actions');
const hud = document.querySelector('#hud');
const ui = Object.fromEntries(['hpfill', 'hptext', 'dashfill', 'dashtext', 'armfill', 'armtext', 'wave', 'waveclock', 'threat', 'ammo', 'stats', 'toast'].map(id => [id, document.getElementById(id)]));

const WORLD = Object.freeze({ w: 1650, h: 1000 });
const TAU = Math.PI * 2;
const KEY = new Set();
const pointer = { x: 0, y: 0, held: false };
const camera = { x: 0, y: 0 };
let width = 0, height = 0, pixelRatio = 1, lastFrame = 0, accumulator = 0;
let gameState = 'menu', player = null, enemies = [], bullets = [], particles = [], pickups = [], hazards = [];
let wave = 1, waveTime = 0, spawnTimer = 0, bossSpawned = false, score = 0, kills = 0;
let shake = 0, freeze = 0, toastTime = 0, toastMessage = '', entityId = 0, runTime = 0;
let muted = false, audio = null;
let lastAim = { x: 1, y: 0 };

const TYPES = Object.freeze({
  worker: { hp: 52, speed: 84, radius: 21, damage: 10, weight: 1, reward: 1, color: '#8db9a2' },
  runner: { hp: 32, speed: 137, radius: 17, damage: 12, weight: 1.15, reward: 1, color: '#edb36c' },
  ranger: { hp: 60, speed: 83, radius: 19, damage: 11, weight: 1, reward: 2, color: '#7cb3d2' },
  brute: { hp: 180, speed: 56, radius: 29, damage: 22, weight: 1.9, reward: 3, color: '#b38fa8' },
  boss: { hp: 1000, speed: 51, radius: 51, damage: 22, weight: 3, reward: 18, color: '#e47882' }
});
const MUTATIONS = [
  { name: 'Mandíbula de hierro', detail: '+30 % de daño', apply: p => p.damage *= 1.30 },
  { name: 'Pies de ultratumba', detail: '+14 % de velocidad', apply: p => p.speed *= 1.14 },
  { name: 'Dedos nerviosos', detail: '+20 % de velocidad de disparo', apply: p => p.fireDelay *= .83 },
  { name: 'Tórax hueco', detail: '+4 balas en el cargador', apply: p => { p.mag += 4; p.ammo += 4; } },
  { name: 'Pulmones sin aire', detail: 'Recargas un 22 % más rápido', apply: p => p.reloadDuration *= .78 },
  { name: 'Costillas blindadas', detail: '+35 de vida máxima y curación', apply: p => { p.maxHp += 35; p.hp = Math.min(p.maxHp, p.hp + 35); } },
  { name: 'Mutación regenerativa', detail: '+1,5 de vida por segundo', apply: p => p.regen += 1.5 },
  { name: 'Brazo espinoso', detail: '+65 % de daño del brazo', apply: p => p.armDamage *= 1.65 },
  { name: 'Brazo veloz', detail: '-30 % de recarga de habilidad', apply: p => p.armCooldown *= .70 },
  { name: 'Articulaciones flexibles', detail: '-28 % de recarga de esquiva', apply: p => p.dashCooldown *= .72 },
  { name: 'Saliva corrosiva', detail: 'Balas perforantes (+1 objetivo)', apply: p => p.pierce += 1 },
  { name: 'Huesos afilados', detail: '+1 proyectil por disparo', apply: p => { p.pellets += 1; p.spread += .075; } },
  { name: 'Ojos podridos', detail: '+18 % de velocidad de proyectil', apply: p => p.bulletSpeed *= 1.18 }
];
// Art integration seam: populate these keys with transparent PNG/WebP URLs later.
// Expected neutral artwork is roughly 96×96 px with feet near the bottom.
const SPRITE_URLS = { zombie: null, worker: null, runner: null, ranger: null, brute: null, boss: null };
const sprites = {};
for (const [kind, url] of Object.entries(SPRITE_URLS)) {
  if (!url) continue;
  const image = new Image();
  image.src = url;
  sprites[kind] = image;
}

const random = (a, b) => a + Math.random() * (b - a);
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const magnitude = (x, y) => Math.hypot(x, y);
const norm = (x, y) => { const m = magnitude(x, y) || 1; return { x: x / m, y: y / m }; };
const distance = (a, b) => magnitude(a.x - b.x, a.y - b.y);
const visible = (x, y, extra = 80) => x - camera.x >= -extra && x - camera.x <= width + extra && y - camera.y >= -extra && y - camera.y <= height + extra;

function resize() {
  width = window.innerWidth; height = window.innerHeight;
  pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.floor(width * pixelRatio); canvas.height = Math.floor(height * pixelRatio);
  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  ctx.imageSmoothingEnabled = true;
  camera.x = clamp(camera.x, 0, Math.max(0, WORLD.w - width));
  camera.y = clamp(camera.y, 0, Math.max(0, WORLD.h - height));
}
window.addEventListener('resize', resize); resize();
function isTextInput(target) { return target?.matches?.('input,textarea,select,[contenteditable]'); }
window.addEventListener('keydown', event => {
  if (isTextInput(event.target)) return;
  const key = event.key.toLowerCase();
  if ([' ', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(key)) event.preventDefault();
  if (key === 'escape' && !event.repeat) {
    if (gameState === 'playing') pauseGame();
    else if (gameState === 'paused') resumeGame();
  }
  if (!event.repeat && gameState === 'playing') {
    if (key === 'r') reload();
    if (key === 'q') throwArm();
  }
  KEY.add(key);
});
window.addEventListener('keyup', event => KEY.delete(event.key.toLowerCase()));
window.addEventListener('blur', () => { KEY.clear(); pointer.held = false; if (gameState === 'playing') pauseGame(); });
window.addEventListener('mousemove', event => { pointer.x = event.clientX; pointer.y = event.clientY; });
canvas.addEventListener('pointerdown', event => {
  if (event.button !== 0) return;
  pointer.x = event.clientX; pointer.y = event.clientY;
  pointer.held = true; initAudio();
});
window.addEventListener('pointerup', event => { if (event.button === 0) pointer.held = false; });
canvas.addEventListener('contextmenu', event => event.preventDefault());

function initAudio() {
  if (muted) return;
  try { audio ??= new (window.AudioContext || window.webkitAudioContext)(); if (audio.state === 'suspended') audio.resume(); } catch { audio = null; }
}
function sound(frequency, duration, type = 'square', volume = .035, slide = 0) {
  if (!audio || muted) return;
  try {
    const osc = audio.createOscillator(), gain = audio.createGain(), now = audio.currentTime;
    osc.type = type;
    osc.frequency.setValueAtTime(Math.max(40, frequency), now);
    osc.frequency.exponentialRampToValueAtTime(Math.max(40, frequency + slide), now + duration);
    gain.gain.setValueAtTime(volume, now);
    gain.gain.exponentialRampToValueAtTime(.0001, now + duration);
    osc.connect(gain).connect(audio.destination);
    osc.start(now); osc.stop(now + duration);
  } catch { /* Audio is optional */ }
}
function toast(message, duration = 1.4) {
  toastTime = duration; toastMessage = message;
  ui.toast.textContent = message;
  ui.toast.classList.add('on');
}
function createParticle(x, y, tint, count = 5, strength = 140) {
  for (let i = 0; i < count; i++) {
    const angle = random(0, TAU), velocity = random(strength * .22, strength);
    particles.push({ x, y, vx: Math.cos(angle) * velocity, vy: Math.sin(angle) * velocity, age: 0, life: random(.18, .45), size: random(2, 6), tint });
  }
  if (particles.length > 650) particles.splice(0, particles.length - 650);
}
function button(label, action, description = '') { return { label, action, description }; }
function showDialog(title, description, buttons, eyebrow = 'HUMANS APOCALYPSE') {
  const h = document.createElement('h1'); h.textContent = title;
  const sub = document.createElement('p'); sub.textContent = description;
  const tag = document.createElement('div'); tag.className = 'eyebrow'; tag.textContent = eyebrow;
  const controls = document.createElement('div'); controls.id = 'actions';
  for (const option of buttons) {
    const el = document.createElement('button');
    el.className = option.description ? 'upgrade' : 'primary';
    if (option.description) {
      const name = document.createElement('b'); name.textContent = option.label;
      const detail = document.createElement('small'); detail.textContent = option.description;
      el.append(name, detail);
    } else el.textContent = option.label;
    el.addEventListener('click', () => { initAudio(); option.action(); });
    controls.append(el);
  }
  panel.replaceChildren(tag, h, sub, controls);
  overlay.classList.remove('hidden');
}
function hideDialog() { overlay.classList.add('hidden'); }
function createPlayer() {
  return {
    x: WORLD.w / 2, y: WORLD.h / 2, radius: 19, hp: 110, maxHp: 110, speed: 255,
    damage: 34, fireDelay: .17, firingTimer: 0, bulletSpeed: 850, pellets: 1, spread: .085, pierce: 0,
    mag: 10, ammo: 10, reloadDuration: .90, reloadTime: 0, regen: 0,
    dashCooldown: 2.5, dashWait: 0, dashTime: 0, dashDx: 0, dashDy: 0,
    armCooldown: 5.2, armWait: 0, armDamage: 72, invuln: 0, recoil: 0,
    aimAngle: 0, facing: 1, travelled: 0
  };
}
function startGame() {
  player = createPlayer();
  enemies = []; bullets = []; particles = []; pickups = []; hazards = [];
  wave = 1; kills = 0; score = 0; runTime = 0; entityId = 0;
  pointer.held = false; KEY.clear();
  hud.classList.remove('hidden');
  beginWave();
  initAudio(); sound(400, .23, 'triangle', .05, 190);
}
function beginWave() {
  waveTime = 20 + 3 * wave; spawnTimer = .7; bossSpawned = false;
  enemies.length = 0; bullets.length = 0; hazards.length = 0;
  player.invuln = 1.0; player.hp = clamp(player.hp + 14, 0, player.maxHp);
  player.ammo = player.mag; player.reloadTime = 0;
  hideDialog(); gameState = 'playing'; toast('OLEADA ' + wave, 1.5);
}
function pauseGame() {
  gameState = 'paused'; pointer.held = false;
  showDialog('EN PAUSA', 'Los humanos esperan. Pulsa continuar para volver al combate.', [button('CONTINUAR', resumeGame), button('REINICIAR PARTIDA', startGame)]);
}
function resumeGame() { gameState = 'playing'; pointer.held = false; hideDialog(); }
function completeWave() {
  if (gameState !== 'playing') return;
  pointer.held = false;
  if (wave === 5) {
    gameState = 'victory'; sound(480, .5, 'triangle', .06, 380);
    showDialog('¡BARRIO SALVADO!', `Has resistido cinco oleadas y derrotado a ${kills} humanos. ADN recogido: ${score}.`, [button('OTRA PARTIDA', startGame)], 'VICTORIA · COMBAT LAB 0.3');
    return;
  }
  gameState = 'upgrade'; sound(750, .23, 'sine', .06, 320);
  const choices = MUTATIONS.map(value => ({ value, sort: Math.random() })).sort((a, b) => a.sort - b.sort).slice(0, 3).map(x => x.value);
  showDialog('MUTACIÓN DISPONIBLE', `Oleada ${wave} superada. Elige una mejora antes de que los humanos regresen.`, choices.map(choice => button(choice.name, () => {
    choice.apply(player); wave++; beginWave();
  }, choice.detail)), 'ADAPTACIÓN ZOMBI');
}
function loseGame() {
  if (gameState !== 'playing') return;
  gameState = 'dead'; pointer.held = false;
  sound(250, .55, 'sawtooth', .05, -175);
  showDialog('TE HAN EXTERMINADO', `Has resistido ${wave} oleadas, eliminado ${kills} humanos y recogido ${score} puntos de ADN.`, [button('REINTENTAR', startGame)], 'FIN DE LA PARTIDA');
}
function spawnEnemy(type) {
  const stats = TYPES[type];
  const angle = random(0, TAU), radius = Math.max(470, Math.min(650, Math.max(width, height) * .65));
  const x = clamp(player.x + Math.cos(angle) * radius, 45, WORLD.w - 45);
  const y = clamp(player.y + Math.sin(angle) * radius, 45, WORLD.h - 45);
  const multiplier = 1 + (wave - 1) * .17;
  const enemy = {
    id: ++entityId, type, x, y, radius: stats.radius, hp: stats.hp * multiplier, maxHp: stats.hp * multiplier,
    speed: stats.speed * (1 + (wave - 1) * .035), damage: stats.damage, mass: stats.weight,
    attack: random(.3, 1.5), windup: 0, charge: 0, rushX: 0, rushY: 0,
    vx: 0, vy: 0, flash: 0, age: 0, angle: 0, strafe: Math.random() < .5 ? -1 : 1
  };
  enemies.push(enemy); return enemy;
}
function spawnPattern() {
  const r = Math.random();
  let type = 'worker';
  if (wave >= 4 && r < .17) type = 'brute';
  else if (wave >= 3 && r < .35) type = 'ranger';
  else if (wave >= 2 && r < .58) type = 'runner';
  return spawnEnemy(type);
}
function reload() {
  if (gameState !== 'playing' || player.reloadTime > 0 || player.ammo === player.mag) return;
  player.reloadTime = player.reloadDuration;
  sound(330, .07, 'triangle', .02, -110);
}
function aimedWorld() { return { x: pointer.x + camera.x, y: pointer.y + camera.y }; }
function shoot() {
  if (player.reloadTime > 0 || player.firingTimer > 0) return;
  if (player.ammo === 0) { reload(); return; }
  const aim = aimedWorld();
  const angle = Math.atan2(aim.y - player.y, aim.x - player.x);
  player.aimAngle = angle;
  player.ammo--; player.firingTimer = player.fireDelay; player.recoil = 1;
  const count = player.pellets;
  for (let i = 0; i < count; i++) {
    const diff = (i - (count - 1) / 2) * player.spread + random(-.016, .016), a = angle + diff;
    bullets.push({
      x: player.x + Math.cos(a) * 30, y: player.y + Math.sin(a) * 30,
      vx: Math.cos(a) * player.bulletSpeed, vy: Math.sin(a) * player.bulletSpeed,
      team: 'zombie', radius: 5.5, damage: player.damage, ttl: .95, pierce: player.pierce,
      hit: new Set(), kind: 'bullet', color: '#e4fb92'
    });
  }
  createParticle(player.x + Math.cos(angle) * 33, player.y + Math.sin(angle) * 33, '#f1fbb0', 4, 80);
  shake = Math.max(shake, 2.1); sound(155, .055, 'sawtooth', .032, -120);
}
function throwArm() {
  if (gameState !== 'playing' || player.armWait > 0) return;
  const aim = aimedWorld(), a = Math.atan2(aim.y - player.y, aim.x - player.x);
  bullets.push({ x: player.x, y: player.y, vx: Math.cos(a) * 590, vy: Math.sin(a) * 590,
    team: 'zombie', radius: 18, damage: player.armDamage, ttl: 1.25, pierce: 99,
    hit: new Set(), kind: 'arm', age: 0, color: '#a6e680' });
  player.armWait = player.armCooldown; shake = 5;
  createParticle(player.x, player.y, '#b9ea8f', 12, 180); sound(270, .18, 'square', .038, -200);
  toast('¡BRAZO VOLADOR!', .65);
}
function spawnHostileProjectile(enemy, angle, speed = 365) {
  bullets.push({ x: enemy.x + Math.cos(angle) * (enemy.radius + 13), y: enemy.y + Math.sin(angle) * (enemy.radius + 13),
    vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, team: 'human', radius: 7.5,
    damage: enemy.damage, ttl: 3.2, kind: 'bullet', color: '#ff9b7d' });
  createParticle(enemy.x, enemy.y, '#ffbe88', 4, 105);
  sound(195, .09, 'triangle', .026, -130);
}
function damagePlayer(amount) {
  if (player.invuln > 0 || gameState !== 'playing') return;
  player.hp -= amount; player.invuln = .53; shake = Math.max(shake, 7);
  createParticle(player.x, player.y, '#ff848a', 14, 210);
  sound(175, .19, 'sawtooth', .055, -115);
  if (player.hp <= 0) { player.hp = 0; loseGame(); }
}
function damageEnemy(enemy, damage, impulseX = 0, impulseY = 0) {
  if (enemy.hp <= 0) return;
  enemy.hp -= damage; enemy.flash = .11; enemy.vx += impulseX / enemy.mass; enemy.vy += impulseY / enemy.mass;
  freeze = Math.max(freeze, .012); shake = Math.max(shake, 2.4);
  createParticle(enemy.x, enemy.y, '#aff58c', 5, 170);
  sound(230, .06, 'triangle', .025, -120);
  if (enemy.hp <= 0) {
    kills++; createParticle(enemy.x, enemy.y, enemy.type === 'boss' ? '#ffae7c' : '#83d98a', enemy.type === 'boss' ? 65 : 18, 235);
    pickups.push({ x: enemy.x, y: enemy.y, kind: 'dna', radius: 10, amount: TYPES[enemy.type].reward });
    if (Math.random() < .075 || enemy.type === 'boss') pickups.push({ x: enemy.x + 24, y: enemy.y + 10, kind: 'heal', radius: 12, amount: 22 });
    sound(360, .11, 'triangle', .045, -270);
  }
}
function movePlayer(dt) {
  const px = (KEY.has('d') || KEY.has('arrowright') ? 1 : 0) - (KEY.has('a') || KEY.has('arrowleft') ? 1 : 0);
  const py = (KEY.has('s') || KEY.has('arrowdown') ? 1 : 0) - (KEY.has('w') || KEY.has('arrowup') ? 1 : 0);
  const movement = norm(px, py), moving = !!(px || py);
  if (moving && player.dashTime <= 0 && KEY.has(' ') && player.dashWait <= 0) {
    player.dashTime = .17; player.dashWait = player.dashCooldown;
    player.dashDx = movement.x; player.dashDy = movement.y;
    player.invuln = Math.max(player.invuln, .23); shake = Math.max(shake, 3);
    createParticle(player.x, player.y, '#8edbd8', 11, 170); sound(410, .14, 'sine', .028, -245);
  }
  const boost = player.dashTime > 0 ? 3.55 : 1;
  const dx = player.dashTime > 0 ? player.dashDx : movement.x;
  const dy = player.dashTime > 0 ? player.dashDy : movement.y;
  player.x = clamp(player.x + dx * player.speed * boost * dt, player.radius + 8, WORLD.w - player.radius - 8);
  player.y = clamp(player.y + dy * player.speed * boost * dt, player.radius + 8, WORLD.h - player.radius - 8);
  player.travelled += dt * (moving ? boost : 0);
  player.dashTime = Math.max(0, player.dashTime - dt);
  player.dashWait = Math.max(0, player.dashWait - dt);
  player.armWait = Math.max(0, player.armWait - dt);
  player.invuln = Math.max(0, player.invuln - dt);
  player.recoil = Math.max(0, player.recoil - dt * 7);
  player.firingTimer = Math.max(0, player.firingTimer - dt);
  player.hp = Math.min(player.maxHp, player.hp + player.regen * dt);
  if (player.reloadTime > 0) {
    player.reloadTime -= dt;
    if (player.reloadTime <= 0) { player.reloadTime = 0; player.ammo = player.mag; sound(660, .075, 'triangle', .025, 200); }
  }
  const aim = aimedWorld(); player.aimAngle = Math.atan2(aim.y - player.y, aim.x - player.x);
  if (pointer.held) shoot();
}
function moveEnemies(dt) {
  for (const enemy of enemies) {
    enemy.age += dt; enemy.flash = Math.max(0, enemy.flash - dt); enemy.attack -= dt;
    const d = distance(enemy, player) || 1;
    const direction = norm(player.x - enemy.x, player.y - enemy.y);
    enemy.angle = Math.atan2(direction.y, direction.x);
    let mx = direction.x, my = direction.y, pace = enemy.speed;
    if (enemy.type === 'ranger') {
      if (d < 270) { mx = -direction.x; my = -direction.y; }
      else if (d < 350) { mx = -direction.y * enemy.strafe; my = direction.x * enemy.strafe; }
      if (enemy.windup > 0) {
        enemy.windup -= dt; pace *= .25;
        if (enemy.windup <= 0) { spawnHostileProjectile(enemy, enemy.angle); enemy.attack = random(1.7, 2.4); }
      } else if (enemy.attack <= 0 && d < 650) { enemy.windup = .52; }
    }
    if (enemy.type === 'runner') {
      if (enemy.charge > 0) {
        enemy.charge -= dt; mx = enemy.rushX; my = enemy.rushY; pace = 385;
      } else if (enemy.windup > 0) {
        enemy.windup -= dt; pace = 0;
        if (enemy.windup <= 0) { enemy.charge = .39; enemy.rushX = direction.x; enemy.rushY = direction.y; enemy.attack = random(2.1, 3.1); }
      } else if (enemy.attack <= 0 && d < 330) { enemy.windup = .40; pace = 0; }
    }
    if (enemy.type === 'brute' && enemy.attack <= 0 && d < 135) {
      enemy.windup = .62; enemy.attack = 3.4;
    }
    if (enemy.type === 'brute' && enemy.windup > 0) {
      enemy.windup -= dt; pace = 0;
      if (enemy.windup <= 0) {
        hazards.push({ x: enemy.x, y: enemy.y, r: 135, age: 0, life: .24, damage: enemy.damage, struck: false });
        sound(95, .17, 'sawtooth', .035, -40);
      }
    }
    if (enemy.type === 'boss') {
      if (enemy.windup > 0) {
        enemy.windup -= dt; pace *= .2;
        if (enemy.windup <= 0) {
          for (let i = -3; i <= 3; i++) spawnHostileProjectile(enemy, enemy.angle + i * .19, 335);
          enemy.attack = 2.5;
        }
      } else if (enemy.attack <= 0 && d < 720) enemy.windup = .8;
    }
    enemy.x = clamp(enemy.x + (mx * pace + enemy.vx) * dt, enemy.radius, WORLD.w - enemy.radius);
    enemy.y = clamp(enemy.y + (my * pace + enemy.vy) * dt, enemy.radius, WORLD.h - enemy.radius);
    enemy.vx *= Math.exp(-10 * dt); enemy.vy *= Math.exp(-10 * dt);
    const after = distance(enemy, player);
    if (after < enemy.radius + player.radius - 3) {
      damagePlayer(enemy.damage);
      const push = norm(enemy.x - player.x, enemy.y - player.y);
      enemy.x += push.x * 25 * dt; enemy.y += push.y * 25 * dt;
    }
  }
}
function updateProjectiles(dt) {
  for (const bullet of bullets) {
    bullet.ttl -= dt;
    if (bullet.kind === 'arm') {
      bullet.age = (bullet.age || 0) + dt;
      if (bullet.age > .47) {
        const seek = norm(player.x - bullet.x, player.y - bullet.y);
        bullet.vx += (seek.x * 810 - bullet.vx) * Math.min(1, dt * 6);
        bullet.vy += (seek.y * 810 - bullet.vy) * Math.min(1, dt * 6);
        if (distance(bullet, player) < 35) bullet.ttl = 0;
      }
    }
    bullet.x += bullet.vx * dt; bullet.y += bullet.vy * dt;
    if (bullet.x < -25 || bullet.y < -25 || bullet.x > WORLD.w + 25 || bullet.y > WORLD.h + 25) bullet.ttl = 0;
    if (bullet.ttl <= 0) continue;
    if (bullet.team === 'human') {
      if (distance(bullet, player) < bullet.radius + player.radius - 3) { damagePlayer(bullet.damage); bullet.ttl = 0; }
      continue;
    }
    for (const enemy of enemies) {
      if (enemy.hp <= 0 || bullet.hit.has(enemy.id)) continue;
      if (distance(bullet, enemy) > bullet.radius + enemy.radius) continue;
      bullet.hit.add(enemy.id);
      const n = norm(bullet.vx, bullet.vy);
      damageEnemy(enemy, bullet.damage, n.x * (bullet.kind === 'arm' ? 530 : 240), n.y * (bullet.kind === 'arm' ? 530 : 240));
      if (bullet.pierce <= 0) { bullet.ttl = 0; break; }
      bullet.pierce--;
    }
  }
  bullets = bullets.filter(bullet => bullet.ttl > 0);
  enemies = enemies.filter(enemy => enemy.hp > 0);
}
function updatePickups(dt) {
  for (const item of pickups) {
    const d = distance(item, player);
    if (d < 170 && d > 0) {
      const step = Math.min(d, dt * (270 + (170 - d) * 4));
      item.x += (player.x - item.x) / d * step;
      item.y += (player.y - item.y) / d * step;
    }
    if (d < item.radius + player.radius) {
      if (item.kind === 'dna') { score += item.amount; sound(940, .07, 'sine', .012, 210); }
      else { player.hp = Math.min(player.maxHp, player.hp + item.amount); toast('+' + item.amount + ' VIDA', .7); sound(600, .12, 'triangle', .035, 240); }
      item.collected = true;
    }
  }
  pickups = pickups.filter(item => !item.collected);
}
function updateHazards(dt) {
  for (const hazard of hazards) {
    hazard.age += dt;
    if (!hazard.struck && hazard.age > .07) {
      hazard.struck = true; createParticle(hazard.x, hazard.y, '#d6a5ad', 20, 275);
      if (distance(hazard, player) < hazard.r + player.radius * .5) damagePlayer(hazard.damage);
    }
  }
  hazards = hazards.filter(hazard => hazard.age < hazard.life);
}
function updateEffects(dt) {
  for (const particle of particles) { particle.age += dt; particle.x += particle.vx * dt; particle.y += particle.vy * dt; particle.vx *= Math.exp(-3 * dt); particle.vy *= Math.exp(-3 * dt); }
  particles = particles.filter(particle => particle.age < particle.life);
  toastTime = Math.max(0, toastTime - dt);
  if (!toastTime) ui.toast.classList.remove('on');
  shake = Math.max(0, shake - dt * 25);
}
function updateHud() {
  ui.hpfill.style.width = `${clamp(player.hp / player.maxHp * 100, 0, 100)}%`;
  ui.hptext.textContent = `${Math.ceil(player.hp)} / ${player.maxHp}`;
  ui.dashfill.style.width = `${100 * (1 - player.dashWait / player.dashCooldown)}%`;
  ui.dashtext.textContent = player.dashWait <= 0 ? 'ESQUIVA LISTA' : 'ESQUIVA ' + player.dashWait.toFixed(1) + 's';
  ui.armfill.style.width = `${100 * (1 - player.armWait / player.armCooldown)}%`;
  ui.armtext.textContent = player.armWait <= 0 ? 'BRAZO LISTO [Q]' : 'BRAZO ' + player.armWait.toFixed(1) + 's';
  ui.wave.textContent = `OLEADA ${wave} / 5`;
  ui.waveclock.textContent = `00:${String(Math.ceil(Math.max(0, waveTime))).padStart(2, '0')}`;
  ui.threat.textContent = waveTime <= 0 ? `ELIMINA LOS RESTANTES (${enemies.length})` : (wave === 5 ? 'ALERTA: EXTERMINADOR' : 'AGUANTA EL ASALTO');
  ui.ammo.textContent = player.reloadTime > 0 ? 'RECARGANDO' : `${player.ammo} / ${player.mag}`;
  ui.ammo.classList.toggle('low', player.ammo < 3 || player.reloadTime > 0);
  ui.stats.textContent = `${kills} HUMANOS · ${score} ADN`;
}
function update(dt) {
  if (!player || gameState !== 'playing') { updateEffects(dt); return; }
  if (freeze > 0) { freeze -= dt; updateEffects(dt); return; }
  runTime += dt;
  const previousTime = waveTime;
  waveTime = Math.max(0, waveTime - dt);
  spawnTimer -= dt;
  movePlayer(dt);
  if (gameState !== 'playing') return;
  if (waveTime > 0 && spawnTimer <= 0 && enemies.length < 55) {
    spawnPattern();
    if (wave >= 3 && Math.random() < .24) spawnPattern();
    spawnTimer = Math.max(.43, 1.18 - wave * .13) * random(.78, 1.16);
  }
  if (wave === 5 && !bossSpawned && previousTime > 14 && waveTime <= 14) {
    bossSpawned = true; const boss = spawnEnemy('boss'); boss.attack = 1.5;
    toast('¡LLEGA EL EXTERMINADOR!', 2.0); sound(125, .55, 'sawtooth', .045, -55);
  }
  moveEnemies(dt);
  updateProjectiles(dt);
  updateHazards(dt);
  updatePickups(dt);
  updateEffects(dt);
  updateHud();
  if (gameState === 'playing' && waveTime === 0 && enemies.length === 0) completeWave();
}

function roundedRect(x, y, w, h, r, fill, stroke = null, lineWidth = 2) {
  if (w <= 0 || h <= 0) return;
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r); ctx.fillStyle = fill; ctx.fill();
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lineWidth; ctx.stroke(); }
}
function circle(x, y, r, fill, stroke = null, lineWidth = 2) {
  ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fillStyle = fill; ctx.fill();
  if (stroke) { ctx.lineWidth = lineWidth; ctx.strokeStyle = stroke; ctx.stroke(); }
}
function drawWorld() {
  ctx.fillStyle = '#1c292b'; ctx.fillRect(0, 0, width, height);
  ctx.save(); ctx.translate(-camera.x, -camera.y);
  roundedRect(0, 0, WORLD.w, WORLD.h, 0, '#233338', '#668478', 12);
  ctx.lineWidth = 1; ctx.strokeStyle = '#3a4e50';
  for (let x = 0; x < WORLD.w; x += 72) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, WORLD.h); ctx.stroke(); }
  for (let y = 0; y < WORLD.h; y += 72) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(WORLD.w, y); ctx.stroke(); }
  ctx.strokeStyle = '#2f4649'; ctx.lineWidth = 3;
  for (let i = 0; i < 16; i++) { const x = 100 + (i * 289) % (WORLD.w - 180), y = 90 + (i * 191) % (WORLD.h - 120); ctx.beginPath(); ctx.moveTo(x - 15, y - 7); ctx.lineTo(x + 11, y + 4); ctx.lineTo(x + 20, y - 6); ctx.stroke(); }
  for (let i = 0; i < 13; i++) { const x = 80 + (i * 223) % (WORLD.w - 150), y = 75 + (i * 157) % (WORLD.h - 150); ctx.globalAlpha = .26; circle(x, y, 10 + (i % 3) * 7, '#78a58c'); }
  ctx.globalAlpha = 1;
  // Street lamps on corners: spatial landmarks, not colliders.
  for (const [x, y] of [[100, 100], [WORLD.w - 100, 100], [100, WORLD.h - 100], [WORLD.w - 100, WORLD.h - 100]]) {
    circle(x, y, 40, '#6ba09a1a'); circle(x, y, 9, '#789d8c'); circle(x, y, 4, '#f0dfa9');
  }
  ctx.restore();
}
function drawActor(kind, x, y, radius, angle = 0, flash = 0, time = 0) {
  const image = sprites[kind];
  if (image?.complete && image.naturalWidth > 0) {
    const size = radius * 3.4;
    ctx.drawImage(image, x - size / 2, y - size * .61, size, size);
    return;
  }
  // Art placeholder: deliberately one function per silhouette, so an artist can replace it cleanly.
  ctx.save(); ctx.translate(x, y);
  const bounce = Math.sin(time * 9) * 1.6;
  ctx.globalAlpha = .27; circle(0, radius * .80, radius * .9, '#061015'); ctx.globalAlpha = 1;
  const zombie = kind === 'zombie';
  const isBoss = kind === 'boss', brute = kind === 'brute', runner = kind === 'runner';
  const coat = zombie ? '#6c9c70' : TYPES[kind]?.color || '#97a6a1';
  const skin = zombie ? '#b2d87f' : '#eac5a2';
  roundedRect(-radius*.49, radius*.20, radius*.42, radius*.74, 4, zombie?'#4c7254':'#33484b');
  roundedRect(radius*.05, radius*.20, radius*.42, radius*.74, 4, zombie?'#4c7254':'#33484b');
  roundedRect(-radius*.73, -radius*.2+bounce, radius*1.46, radius*1.12, radius*.36, flash > 0 ? '#f8fff1' : coat, '#12282b', 2.6);
  // Clear character silhouette and uniform.
  if (kind === 'ranger') { roundedRect(-radius*.12, -radius*.18+bounce, radius*.25, radius*.85, 2, '#e8e6d1'); }
  if (brute || isBoss) { roundedRect(-radius*.85, -radius*.20+bounce, radius*1.70, radius*.25, 3, '#59666b'); }
  circle(0, -radius*.43+bounce, radius*.67, flash > 0 ? '#fbfff9' : skin, '#23312f', 2.6);
  if (zombie) {
    ctx.fillStyle='#355345'; ctx.beginPath(); ctx.moveTo(-radius*.73,-radius*.65+bounce);ctx.lineTo(-radius*.45,-radius*1.03+bounce);ctx.lineTo(radius*.13,-radius*.87+bounce);ctx.lineTo(radius*.65,-radius*.68+bounce);ctx.closePath();ctx.fill();
    circle(-radius*.22, -radius*.48+bounce, radius*.13, '#fcffff'); circle(radius*.24, -radius*.48+bounce, radius*.16, '#fcffff');
    circle(-radius*.22, -radius*.47+bounce, radius*.058, '#1b3029'); circle(radius*.23, -radius*.47+bounce, radius*.067, '#1b3029');
    roundedRect(-radius*.23, -radius*.15+bounce, radius*.48, radius*.12, 2, '#34563a');
    roundedRect(-radius*.08, -radius*.15+bounce, radius*.10, radius*.17, 1, '#eff6d1');
  } else {
    roundedRect(-radius*.30, -radius*.5+bounce, radius*.18, radius*.09, 1, '#392b2b');roundedRect(radius*.12, -radius*.5+bounce, radius*.18, radius*.09, 1, '#392b2b');
    if (runner) { roundedRect(-radius*.85, -radius*1.03+bounce, radius*1.7, radius*.28, 4, '#c77a39'); }
    if (kind === 'worker') { roundedRect(-radius*.78, -radius*.96+bounce, radius*1.56, radius*.24, 4, '#718e74'); }
    if (isBoss) { roundedRect(-radius*.8, -radius*1.14+bounce, radius*1.6, radius*.33, 4, '#ee7c77'); }
  }
  // Arm, pointing roughly towards movement / aiming.
  ctx.rotate(angle);
  roundedRect(radius*.30, -radius*.02, radius*.67, radius*.28, 4, flash > 0 ? '#fff' : coat, '#223237', 2);
  if (kind === 'ranger' || isBoss) roundedRect(radius*.72, -radius*.06, radius*.72, radius*.18, 3, '#313b44');
  if (zombie) { roundedRect(radius*.54, -radius*.12, radius*1.08, radius*.34, 3, '#3c4c58', '#14282a', 2); roundedRect(radius*1.32, -radius*.17, radius*.31, radius*.10, 2, '#b4c1a4'); }
  ctx.restore();
}
function drawEffects() {
  for (const hazard of hazards) {
    circle(hazard.x, hazard.y, hazard.r * (hazard.age / hazard.life), '#e0a0b33a', '#ffd9b388', 3);
  }
  for (const pickup of pickups) {
    const bob = Math.sin(runTime * 4 + pickup.x) * 3;
    circle(pickup.x, pickup.y + bob, pickup.radius, pickup.kind === 'heal' ? '#e27c75' : '#9ee3c8', '#edf6da', 2);
    ctx.fillStyle = '#2c5544'; ctx.font = '900 11px system-ui'; ctx.textAlign = 'center'; ctx.fillText(pickup.kind === 'heal' ? '+' : '●', pickup.x, pickup.y + bob + 3);
  }
  for (const bullet of bullets) {
    if (bullet.kind === 'arm') {
      ctx.save();ctx.translate(bullet.x, bullet.y);ctx.rotate(runTime * 10);
      roundedRect(-9, -10, 22, 20, 5, '#9ace80', '#294a3b');
      for (let i = -1; i <= 1; i++) roundedRect(8, i * 7 - 3, 16, 5, 3, '#bde79c', '#284139', 1);
      ctx.restore(); continue;
    }
    ctx.strokeStyle = bullet.team === 'human' ? '#f48f74' : '#dcf99a'; ctx.lineWidth = 4;
    ctx.beginPath();ctx.moveTo(bullet.x - bullet.vx * .015, bullet.y - bullet.vy * .015);ctx.lineTo(bullet.x,bullet.y);ctx.stroke();
    circle(bullet.x, bullet.y, bullet.radius, bullet.color);
  }
  for (const particle of particles) {
    ctx.globalAlpha = 1 - particle.age / particle.life;
    ctx.fillStyle = particle.tint; ctx.fillRect(particle.x - particle.size*.5, particle.y - particle.size*.5, particle.size, particle.size);
  }
  ctx.globalAlpha = 1;
}
function draw() {
  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  ctx.clearRect(0, 0, width, height);
  if (player) {
    camera.x = clamp(player.x - width*.5, 0, Math.max(0, WORLD.w - width));
    camera.y = clamp(player.y - height*.5, 0, Math.max(0, WORLD.h - height));
  } else { camera.x = clamp((WORLD.w - width) / 2, 0, Math.max(0, WORLD.w - width)); camera.y = clamp((WORLD.h - height) / 2, 0, Math.max(0, WORLD.h - height)); }
  ctx.save();
  if (shake > 0 && gameState === 'playing') ctx.translate(random(-shake, shake), random(-shake, shake));
  drawWorld();
  ctx.save(); ctx.translate(-camera.x, -camera.y);
  if (player) {
    for (const enemy of enemies) {
      if (!visible(enemy.x, enemy.y, 95)) continue;
      if (enemy.windup > 0) {
        if (enemy.type === 'brute') {
          circle(enemy.x, enemy.y, 135, '#cf777522', '#ff8f8099', 3);
        } else if (enemy.type === 'runner') {
          ctx.strokeStyle = '#f9b77b';ctx.lineWidth = 5;ctx.beginPath();ctx.moveTo(enemy.x,enemy.y);ctx.lineTo(enemy.x + Math.cos(enemy.angle) * 125, enemy.y + Math.sin(enemy.angle)*125);ctx.stroke();
        } else if (enemy.type === 'ranger' || enemy.type === 'boss') {
          ctx.strokeStyle = '#ffa18f';ctx.lineWidth = 2.5;ctx.setLineDash([8, 7]);ctx.beginPath();ctx.moveTo(enemy.x,enemy.y);ctx.lineTo(player.x,player.y);ctx.stroke();ctx.setLineDash([]);
        }
      }
      drawActor(enemy.type, enemy.x, enemy.y, enemy.radius, enemy.angle, enemy.flash, enemy.age);
      const w = enemy.radius * 2.1;
      roundedRect(enemy.x - w*.5, enemy.y - enemy.radius*1.5 - 10, w, 6, 2, '#11232d');
      roundedRect(enemy.x - w*.5, enemy.y - enemy.radius*1.5 - 10, w * Math.max(0, enemy.hp/enemy.maxHp), 6, 2, '#f19b95');
    }
    if (player.dashTime > 0) { ctx.globalAlpha = .25; circle(player.x - player.dashDx * 34, player.y - player.dashDy * 34, player.radius, '#b7f7bf'); ctx.globalAlpha = 1; }
    if (!(player.invuln > 0 && Math.floor(runTime*18)%2 === 0)) drawActor('zombie', player.x, player.y, player.radius, player.aimAngle, 0, player.travelled);
    drawEffects();
  }
  ctx.restore();
  ctx.restore();
  if (player && gameState === 'playing') {
    // Crosshair: correctly aligned even when camera scrolls.
    const x = pointer.x, y = pointer.y;
    ctx.strokeStyle = '#e9f9d9'; ctx.lineWidth = 2;ctx.beginPath();
    ctx.moveTo(x-15,y);ctx.lineTo(x-6,y);ctx.moveTo(x+6,y);ctx.lineTo(x+15,y);
    ctx.moveTo(x,y-15);ctx.lineTo(x,y-6);ctx.moveTo(x,y+6);ctx.lineTo(x,y+15);ctx.stroke();
    circle(x,y,2,'#e8fae2');
  }
}
function frame(timestamp) {
  if (!lastFrame) lastFrame = timestamp;
  const dt = Math.min((timestamp - lastFrame)/1000, .08); lastFrame = timestamp;
  accumulator = Math.min(.15, accumulator + dt);
  const fixed = 1/60;
  while (accumulator >= fixed) { update(fixed); accumulator -= fixed; }
  draw();
  window.requestAnimationFrame(frame);
}
// Initial layout / decorative world can draw before game starts.
window.requestAnimationFrame(frame);
document.getElementById('start').addEventListener('click', startGame);
// Lightweight public test API to help automate browser smoke tests.
window.__humansApocalypse = Object.freeze({
  getSnapshot: () => ({
    state: gameState, wave, kills, score, enemyCount: enemies.length,
    player: player && { x: player.x, y: player.y, hp: player.hp, ammo: player.ammo, mag: player.mag, dashWait: player.dashWait, armWait: player.armWait },
    bullets: bullets.length
  }),
  version: '0.3.0'
});
