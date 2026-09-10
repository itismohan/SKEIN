const progress=document.getElementById("progress");
const year=document.getElementById("year");
year.textContent=new Date().getFullYear();

window.addEventListener("scroll",()=>{
  const max=document.documentElement.scrollHeight-window.innerHeight;
  progress.style.width=(max>0?(window.scrollY/max)*100:0)+"%";
},{passive:true});

const navToggle=document.getElementById("navToggle");
const navLinks=document.getElementById("navLinks");
navToggle?.addEventListener("click",()=>{
  const open=navLinks.classList.toggle("open");
  navToggle.setAttribute("aria-expanded",String(open));
});
document.querySelectorAll(".nav-links a").forEach(a=>a.addEventListener("click",()=>navLinks.classList.remove("open")));

const observer=new IntersectionObserver(entries=>{
  entries.forEach(entry=>{if(entry.isIntersecting)entry.target.classList.add("in")});
},{threshold:.12});
document.querySelectorAll(".reveal").forEach(el=>observer.observe(el));

const codeBlocks={
  install:`git clone https://github.com/itismohan/SKEIN.git
cd SKEIN

python -m venv .venv
source .venv/bin/activate
pip install -e .

skein init .
skein ingest .
skein dashboard .`,
  mcp:`# Start MCP over stdio
skein mcp-stdio .

# Or HTTP
skein mcp-http . --host 127.0.0.1 --port 8765`,
  dashboard:`# Build the local governance dashboard
skein dashboard . --output .skein/dashboard.html

# Run release validation
skein release-check .
skein hardening .
skein certify .`
};
document.querySelectorAll(".tab").forEach(tab=>{
  tab.addEventListener("click",()=>{
    document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));
    tab.classList.add("active");
    const key=tab.dataset.tab;
    document.getElementById("install-code").textContent=codeBlocks[key];
  });
});
document.querySelector(".copy-btn")?.addEventListener("click",async e=>{
  const target=document.getElementById(e.currentTarget.dataset.copyTarget);
  try{
    await navigator.clipboard.writeText(target.textContent);
    e.currentTarget.textContent="Copied";
    setTimeout(()=>e.currentTarget.textContent="Copy",1200);
  }catch{e.currentTarget.textContent="Select & copy"}
});

const sections=[...document.querySelectorAll("main section[id]")];
const navAnchors=[...document.querySelectorAll(".nav-links a[href^='#']")];
const sectionObserver=new IntersectionObserver(entries=>{
  entries.forEach(entry=>{
    if(entry.isIntersecting){
      navAnchors.forEach(a=>a.classList.toggle("active",a.getAttribute("href")==="#"+entry.target.id));
    }
  });
},{rootMargin:"-35% 0px -55% 0px",threshold:0});
sections.forEach(s=>sectionObserver.observe(s));
