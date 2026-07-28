const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const minimapCanvas = document.getElementById('minimap');
const mctx = minimapCanvas.getContext('2d');

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  minimapCanvas.width = 140;
  minimapCanvas.height = 140;
}
window.addEventListener('resize', resize);
resize();

let myId = null;
let selectedClass = 'Attacker';
let players = {};
let bullets = [];
let orbs = [];
let mapWidth = 2500;
let mapHeight = 2500;

let wantShoot = false;
let shootAngle = 0;

const keys = {};
const mouse = { x: 0, y: 0, worldX: 0, worldY: 0 };

window.addEventListener('keydown', e => keys[e.key.toLowerCase()] = true);
window.addEventListener('keyup', e => keys[e.key.toLowerCase()] = false);
window.addEventListener('mousemove', e => {
  mouse.x = e.clientX;
  mouse.y = e.clientY;
});
window.addEventListener('mousedown', e => {
  if (e.button === 0 && myId && players[myId] && players[myId].hp > 0) {
    wantShoot = true;
    const p = players[myId];
    shootAngle = Math.atan2(mouse.worldY - p.y, mouse.worldX - p.x);
  }
});

function selectClass(className, btn) {
  selectedClass = className;
  document.querySelectorAll('.class-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

async function joinGame() {
  const name = document.getElementById('playerName').value || 'Hero';
  const res = await fetch('/api/join', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name, class: selectedClass })
  });
  const data = await res.json();
  myId = data.id;
  mapWidth = data.mapWidth;
  mapHeight = data.mapHeight;
  
  document.getElementById('startScreen').style.display = 'none';
  startSyncLoop();
}

function respawn() {
  document.getElementById('deathScreen').style.display = 'none';
  joinGame();
}

function startSyncLoop() {
  setInterval(async () => {
    if (!myId || !players[myId]) return;
    const p = players[myId];
    
    let dx = 0, dy = 0;
    if (keys['w'] || keys['arrowup']) dy -= 1;
    if (keys['s'] || keys['arrowdown']) dy += 1;
    if (keys['a'] || keys['arrowleft']) dx -= 1;
    if (keys['d'] || keys['arrowright']) dx += 1;
    
    if (dx !== 0 || dy !== 0) {
      const len = Math.hypot(dx, dy);
      p.x += (dx / len) * p.speed;
      p.y += (dy / len) * p.speed;
    }

    mouse.worldX = mouse.x - canvas.width / 2 + p.x;
    mouse.worldY = mouse.y - canvas.height / 2 + p.y;
    const angle = Math.atan2(mouse.worldY - p.y, mouse.worldX - p.x);

    const payload = {
      id: myId,
      x: p.x,
      y: p.y,
      angle: angle,
      shoot: wantShoot,
      shootAngle: shootAngle
    };
    wantShoot = false;

    try {
      const res = await fetch('/api/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const state = await res.json();
      players = state.players;
      bullets = state.bullets;
      orbs = state.orbs;

      if (players[myId] && players[myId].hp <= 0) {
        document.getElementById('deathScreen').style.display = 'flex';
      }
      updateHUD();
    } catch(err) {}
  }, 50);
}

function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const self = players[myId] || { x: mapWidth / 2, y: mapHeight / 2 };
  
  ctx.save();
  ctx.translate(canvas.width / 2 - self.x, canvas.height / 2 - self.y);
  
  // Arena Grid
  ctx.strokeStyle = '#1e272e';
  ctx.lineWidth = 2;
  for (let x = 0; x < mapWidth; x += 100) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, mapHeight); ctx.stroke();
  }
  for (let y = 0; y < mapHeight; y += 100) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(mapWidth, y); ctx.stroke();
  }

  // Orbs
  orbs.forEach(o => {
    ctx.beginPath();
    ctx.arc(o.x, o.y, 8, 0, Math.PI * 2);
    ctx.fillStyle = o.type === 'health' ? '#2ed573' : (o.type === 'speed' ? '#eccc68' : (o.type === 'damage' ? '#ff4757' : '#00d2ff'));
    ctx.fill();
  });

  // Bullets
  bullets.forEach(b => {
    ctx.beginPath();
    ctx.arc(b.x, b.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#ffa502';
    ctx.fill();
  });

  // Players
  Object.values(players).forEach(p => {
    if (p.hp <= 0) return;
    ctx.save();
    ctx.translate(p.x, p.y);
    if (p.shield) {
      ctx.beginPath(); ctx.arc(0, 0, 35, 0, Math.PI * 2);
      ctx.strokeStyle = '#70a1ff'; ctx.lineWidth = 3; ctx.stroke();
    }
    ctx.rotate(p.angle);
    ctx.fillStyle = p.class === 'Defender' ? '#e1b12c' : (p.class === 'Scout' ? '#44bd32' : '#00a8ff');
    ctx.fillRect(-20, -20, 40, 40);
    ctx.fillStyle = '#2f3640';
    ctx.fillRect(0, -5, 28, 10);
    ctx.restore();
    
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 12px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`${p.name} [Lv.${p.level}]`, p.x, p.y - 32);
    
    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.fillRect(p.x - 25, p.y - 26, 50, 6);
    ctx.fillStyle = '#2ed573';
    ctx.fillRect(p.x - 25, p.y - 26, (p.hp / p.maxHp) * 50, 6);
  });

  ctx.restore();
  
  // Minimap
  mctx.clearRect(0, 0, 140, 140);
  const scaleX = 140 / mapWidth;
  const scaleY = 140 / mapHeight;
  Object.values(players).forEach(p => {
    if (p.hp <= 0) return;
    mctx.fillStyle = p.id === myId ? '#2ed573' : '#ff4757';
    mctx.beginPath();
    mctx.arc(p.x * scaleX, p.y * scaleY, 3, 0, Math.PI * 2);
    mctx.fill();
  });

  requestAnimationFrame(render);
}

function updateHUD() {
  if (!myId || !players[myId]) return;
  const p = players[myId];
  document.getElementById('hpFill').style.width = `${Math.max(0, (p.hp / p.maxHp) * 100)}%`;
  document.getElementById('hpText').innerText = `HP: ${Math.ceil(p.hp)} / ${p.maxHp}`;
  
  const xpNeeded = p.level * 150;
  document.getElementById('xpFill').style.width = `${Math.min(100, (p.xp / xpNeeded) * 100)}%`;
  document.getElementById('xpText').innerText = `LEVEL ${p.level} (${p.class.toUpperCase()})`;

  const sorted = Object.values(players).sort((a,b) => b.score - a.score).slice(0, 5);
  const list = document.getElementById('leaderList');
  list.innerHTML = '';
  sorted.forEach((lp, i) => {
    const row = document.createElement('div');
    row.className = 'leader-row';
    row.innerHTML = `<span>${i+1}. ${lp.name}</span><strong>${lp.score}</strong>`;
    list.appendChild(row);
  });
}

requestAnimationFrame(render);
