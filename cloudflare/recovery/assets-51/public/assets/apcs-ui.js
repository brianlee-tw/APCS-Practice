(()=>{
  const root=document.documentElement;
  const stored=localStorage.getItem('apcs-theme')||'system';
  const resolved=stored==='system'?(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'):stored;
  root.dataset.theme=resolved;
  window.APCS_UI={
    esc:x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
    theme(){const cur=localStorage.getItem('apcs-theme')||'system';const next=cur==='system'?'dark':cur==='dark'?'light':'system';localStorage.setItem('apcs-theme',next);const actual=next==='system'?(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'):next;root.dataset.theme=actual;return next},
    toast(title,body){let t=document.querySelector('.toast');if(!t){t=document.createElement('div');t.className='toast';t.innerHTML='<b></b><p></p>';document.body.appendChild(t)}t.querySelector('b').textContent=title;t.querySelector('p').textContent=body;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),3000)},
    fmt:n=>Number(n).toLocaleString('en-US')
  };
})();
