// Nucleo da plataforma Morumbi 3D -- o que TODO gerador usa igual.
//
// Saiu de dentro de web/gerador-letreiros.html no sprint C1. Ali dentro ele
// era util para exatamente um gerador; aqui e o chao dos proximos. A regra do
// que entra neste arquivo e a tabela "plataforma x peca" do plano: desenhar a
// peca e da peca, TODO o resto e daqui -- poligono, solido, STL, o que cabe na
// mesa, quanto pesa, quanto custa e como o arquivo se chama.
//
// Nao ha nada de letreiro aqui. Se aparecer, esta no arquivo errado.
//
// Carrega em navegador (<script src>) e em node (require), porque as
// ferramentas de conferencia rodam nos dois.
(function (root, fabrica) {
  const M = fabrica(root);
  if (typeof module === 'object' && module.exports) module.exports = M;
  else root.MorumbiNucleo = M;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {
  const S = 10000, FT = 1;
  const MESA = 256;       // mm: lado util da mesa da impressora

  function api() { return root.ClipperLib || require('clipper-lib'); }
  function ec() { const m = root.earcut || require('earcut'); return m.default || m; }

  const cub = (a,b,c,d,t) => { const u=1-t; return u*u*u*a + 3*u*u*t*b + 3*u*t*t*c + t*t*t*d; };
  const qua = (a,b,c,t) => { const u=1-t; return u*u*a + 2*u*t*b + t*t*c; };

  function pathToPolys(path, segs) {
    segs = segs || 14;
    const polys = []; let cur = null, px=0, py=0, sx=0, sy=0;
    const add = (x,y) => cur.push({ X: Math.round(x*S), Y: Math.round(-y*S) });
    for (const c of path.commands) {
      if (c.type==='M'){ if(cur&&cur.length>2)polys.push(cur); cur=[]; add(c.x,c.y); px=sx=c.x; py=sy=c.y; }
      else if (c.type==='L'){ add(c.x,c.y); px=c.x; py=c.y; }
      else if (c.type==='C'){ for(let i=1;i<=segs;i++){const t=i/segs; add(cub(px,c.x1,c.x2,c.x,t), cub(py,c.y1,c.y2,c.y,t));} px=c.x; py=c.y; }
      else if (c.type==='Q'){ for(let i=1;i<=segs;i++){const t=i/segs; add(qua(px,c.x1,c.x,t), qua(py,c.y1,c.y,t));} px=c.x; py=c.y; }
      else if (c.type==='Z'){ if(cur&&cur.length>2)polys.push(cur); cur=null; px=sx; py=sy; }
    }
    if (cur && cur.length>2) polys.push(cur);
    return polys;
  }

  function uniao(lista) {
    const L=api(), c=new L.Clipper(), sol=new L.Paths();
    lista.forEach(p => { if (p && p.length) c.AddPaths(p, 0, true); });
    c.Execute(L.ClipType.ctUnion, sol, FT, FT);
    return sol;
  }
  function diferenca(a, b) {
    const L=api(), c=new L.Clipper(), sol=new L.Paths();
    c.AddPaths(a,0,true); c.AddPaths(b,1,true);
    c.Execute(L.ClipType.ctDifference, sol, FT, FT);
    return sol;
  }
  function inflar(paths, d) {
    const L=api(), co=new L.ClipperOffset(2, 0.25), sol=new L.Paths();
    co.AddPaths(paths, L.JoinType.jtRound, L.EndType.etClosedPolygon);
    co.Execute(sol, d*S);
    return sol;
  }
  function mover(paths, dx, dy) {
    const ix=Math.round((dx||0)*S), iy=Math.round((dy||0)*S);
    return paths.map(p => p.map(pt => ({ X: pt.X+ix, Y: pt.Y+iy })));
  }
  function escalar(paths, s) {
    return paths.map(p => p.map(pt => ({ X: Math.round(pt.X*s), Y: Math.round(pt.Y*s) })));
  }
  function caixa(paths) {
    let a=Infinity,b=-Infinity,c=Infinity,d=-Infinity;
    for (const p of paths) for (const pt of p) {
      if(pt.X<a)a=pt.X; if(pt.X>b)b=pt.X; if(pt.Y<c)c=pt.Y; if(pt.Y>d)d=pt.Y;
    }
    return { minX:a/S, maxX:b/S, minY:c/S, maxY:d/S, w:(b-a)/S, h:(d-c)/S };
  }
  function analisar(paths) {
    const L=api(); let corpos=0, vazados=0;
    for (const p of paths) (L.Clipper.Area(p) > 0 ? corpos++ : vazados++);
    return { corpos, vazados };
  }
  function retangulo(x0, y0, x1, y1) {
    const q = v => Math.round(v*S);
    return [[{X:q(x0),Y:q(y0)}, {X:q(x1),Y:q(y0)}, {X:q(x1),Y:q(y1)}, {X:q(x0),Y:q(y1)}]];
  }

  // ---------- STL ----------
  function grupos(paths) {
    const L=api(), c=new L.Clipper(), tree=new L.PolyTree();
    c.AddPaths(paths, 0, true); c.Execute(L.ClipType.ctUnion, tree, FT, FT);
    const out=[], pilha=tree.m_Childs.slice();
    while (pilha.length) {
      const n = pilha.pop();
      if (!n.IsHole()) {
        const buracos=[];
        for (const f of n.m_Childs) { buracos.push(f.m_polygon); pilha.push(...f.m_Childs); }
        out.push({ outer:n.m_polygon, buracos });
      } else pilha.push(...n.m_Childs);
    }
    return out;
  }
  function tampa(paths, z, cima) {
    const tris=[];
    for (const g of grupos(paths)) {
      const v=[], hi=[];
      const push = p => { for (const pt of p) v.push(pt.X/S, pt.Y/S); };
      push(g.outer);
      for (const b of g.buracos) { hi.push(v.length/2); push(b); }
      const idx = ec()(v, hi, 2);
      for (let i=0;i<idx.length;i+=3) {
        const P = k => [v[k*2], v[k*2+1], z];
        const a=P(idx[i]), b=P(idx[i+1]), c=P(idx[i+2]);
        tris.push(cima ? [a,b,c] : [a,c,b]);
      }
    }
    return tris;
  }
  function paredes(paths, z0, z1) {
    const tris=[];
    for (const g of grupos(paths)) for (const ct of [g.outer].concat(g.buracos)) {
      for (let i=0;i<ct.length;i++) {
        const p=ct[i], q=ct[(i+1)%ct.length];
        const x1=p.X/S,y1=p.Y/S,x2=q.X/S,y2=q.Y/S;
        if (x1===x2 && y1===y2) continue;
        tris.push([[x1,y1,z0],[x2,y2,z0],[x2,y2,z1]]);
        tris.push([[x1,y1,z0],[x2,y2,z1],[x1,y1,z1]]);
      }
    }
    return tris;
  }
  // Junta em T: vertice pousado no MEIO da aresta de outra face. Acontece
  // onde uma camada tem um recorte que a de cima nao tem — o rasgo do cabo
  // da luminaria e o caso classico. A geometria esta certa, mas a aresta
  // fica sem par e o fatiador ve a malha como aberta.
  //
  // O conserto e local: acha a aresta de borda, junta TODOS os vertices que
  // estao em cima dela e divide o triangulo dono em leque. Dividir um ponto
  // por vez nao resolve quando ha varios na mesma aresta.
  function costurarJuntasT(tris, tol) {
    tol = tol || 1e-4;
    const chave = p => p[0].toFixed(4) + ',' + p[1].toFixed(4) + ',' + p[2].toFixed(4);
    const indice = new Map(), vertices = [];
    let faces = [];
    for (const t of tris) {
      const f = [];
      for (const p of t) {
        const k = chave(p);
        let i = indice.get(k);
        if (i === undefined) { i = vertices.length; indice.set(k, i); vertices.push(p); }
        f.push(i);
      }
      if (f[0] !== f[1] && f[1] !== f[2] && f[0] !== f[2]) faces.push(f);
    }

    const dist = (a, b) => Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2]);
    for (let volta = 0; volta < 6; volta++) {
      const conta = new Map();
      for (const [a,b,c] of faces) for (const [i,j] of [[a,b],[b,c],[c,a]]) {
        const k = i < j ? i+'_'+j : j+'_'+i;
        conta.set(k, (conta.get(k) || 0) + 1);
      }
      const bordas = [];
      for (const [k,n] of conta) if (n === 1) bordas.push(k.split('_').map(Number));
      if (!bordas.length) break;

      const candidatos = new Set();
      for (const [i,j] of bordas) { candidatos.add(i); candidatos.add(j); }

      const corte = new Map();
      for (const [i,j] of bordas) {
        const a = vertices[i], b = vertices[j], L = dist(a,b);
        if (L < tol) continue;
        const dentro = [];
        for (const v of candidatos) {
          if (v === i || v === j) continue;
          const p = vertices[v];
          const t = ((p[0]-a[0])*(b[0]-a[0]) + (p[1]-a[1])*(b[1]-a[1]) + (p[2]-a[2])*(b[2]-a[2])) / (L*L);
          if (!(t > 1e-9 && t < 1-1e-9)) continue;
          const proj = [a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t, a[2]+(b[2]-a[2])*t];
          if (dist(p, proj) > tol) continue;
          dentro.push([t, v]);
        }
        if (dentro.length) {
          dentro.sort((x,y) => x[0]-y[0]);
          corte.set(i+'_'+j, dentro.map(d => d[1]));
        }
      }
      if (!corte.size) break;

      const novas = [];
      for (const face of faces) {
        let dividiu = false;
        for (let k = 0; k < 3; k++) {
          const a = face[k], b = face[(k+1)%3], c = face[(k+2)%3];
          const direto = corte.get(a+'_'+b), inverso = corte.get(b+'_'+a);
          if (!direto && !inverso) continue;
          const meio = direto ? direto : inverso.slice().reverse();
          const corrente = [a].concat(meio, [b]);
          for (let n = 0; n < corrente.length-1; n++) novas.push([corrente[n], corrente[n+1], c]);
          dividiu = true;
          break;
        }
        if (!dividiu) novas.push(face);
      }
      faces = novas;
    }
    return faces.map(f => f.map(i => vertices[i]));
  }

  function stlBinario(camadas) {
    let tris = tampa(camadas[0].paths, camadas[0].z0, false);
    for (let i=0;i<camadas.length;i++) {
      const c = camadas[i];
      tris = tris.concat(paredes(c.paths, c.z0, c.z1));
      if (i < camadas.length-1) {
        const n = camadas[i+1];
        const sobe = diferenca(c.paths, n.paths); if (sobe.length) tris = tris.concat(tampa(sobe, c.z1, true));
        const desce = diferenca(n.paths, c.paths); if (desce.length) tris = tris.concat(tampa(desce, c.z1, false));
      }
    }
    const u = camadas[camadas.length-1];
    tris = tris.concat(tampa(u.paths, u.z1, true));
    tris = costurarJuntasT(tris);

    const buf = new ArrayBuffer(84 + tris.length*50), dv = new DataView(buf);
    dv.setUint32(80, tris.length, true);
    let o = 84;
    for (const t of tris) {
      const ux=t[1][0]-t[0][0], uy=t[1][1]-t[0][1], uz=t[1][2]-t[0][2];
      const vx=t[2][0]-t[0][0], vy=t[2][1]-t[0][1], vz=t[2][2]-t[0][2];
      let nx=uy*vz-uz*vy, ny=uz*vx-ux*vz, nz=ux*vy-uy*vx;
      const m = Math.hypot(nx,ny,nz)||1;
      dv.setFloat32(o,nx/m,true); dv.setFloat32(o+4,ny/m,true); dv.setFloat32(o+8,nz/m,true); o+=12;
      for (const q of t) { dv.setFloat32(o,q[0],true); dv.setFloat32(o+4,q[1],true); dv.setFloat32(o+8,q[2],true); o+=12; }
      dv.setUint16(o,0,true); o+=2;
    }
    return { buffer: buf, n: tris.length };
  }

  return { S, FT, MESA, cub, qua, pathToPolys, uniao, diferenca, inflar, mover,
           escalar, caixa, analisar, retangulo, grupos, stlBinario };
});
