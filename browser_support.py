"""YouTube Music request filtering and drag-link extraction."""
from urllib.parse import urlparse
BLOCKED_DOMAINS=frozenset({'doubleclick.net','googleadservices.com','googlesyndication.com','google-analytics.com','googletagmanager.com','adservice.google.com','ads.youtube.com'})
def blocked_request(url):
    parsed=urlparse(url);host=(parsed.hostname or '').lower()
    if any(host==domain or host.endswith('.'+domain) for domain in BLOCKED_DOMAINS):return True
    return host in ('youtube.com','www.youtube.com','music.youtube.com') and parsed.path.startswith(('/api/stats/ads','/pagead/','/get_midroll_info'))

DRAG_SCRIPT=r'''
if (location.hostname === 'music.youtube.com') {
 document.addEventListener('dragstart', event => {
   let node=event.target instanceof Element?event.target:null;
   let href='';
   const anchor=node?.closest('a[href]');
   if(anchor)href=anchor.href;
   const row=node?.closest('ytmusic-responsive-list-item-renderer,ytmusic-two-row-item-renderer,ytmusic-player-bar');
   if(!href&&row){
     const link=row.querySelector('a[href*="watch?v="]');
     if(link)href=link.href;
     const data=row.data;
     const id=data?.playlistItemData?.videoId||data?.navigationEndpoint?.watchEndpoint?.videoId||data?.playNavigationEndpoint?.watchEndpoint?.videoId;
     if(!href&&id)href='https://music.youtube.com/watch?v='+id;
   }
   try{const url=new URL(href);const id=url.searchParams.get('v');if(!/^[A-Za-z0-9_-]{11}$/.test(id||''))return;
     const clean='https://music.youtube.com/watch?v='+id;
     event.dataTransfer.setData('text/uri-list',clean);event.dataTransfer.setData('text/plain',clean);event.dataTransfer.effectAllowed='copy';
   }catch{}
 },true);
 const mark=()=>document.querySelectorAll('a[href*="watch?v="],ytmusic-responsive-list-item-renderer,ytmusic-two-row-item-renderer').forEach(n=>n.draggable=true);
 let pending=false;const observer=new MutationObserver(()=>{if(pending)return;pending=true;setTimeout(()=>{pending=false;mark()},350)});
 observer.observe(document.documentElement,{childList:true,subtree:true});mark();
}
'''
COSMETIC_SCRIPT=r'''
(() => {const id='aural-ad-filter';let style=document.getElementById(id);
 if(ENABLED){if(!style){style=document.createElement('style');style.id=id;style.textContent='ytmusic-ad-slot-renderer,ytmusic-mealbar-promo-renderer{display:none!important}';document.documentElement.append(style)}}else style?.remove();})()
'''

# Apply the selected accent without changing site content or navigation.
def music_theme_script(accent, surface):
    import json
    css=f'''
    :root, ytmusic-app {{
      --aural-accent: {accent}; --aural-surface: {surface};
      --ytmusic-color-black1: #121512;
      --ytmusic-color-black2: {surface};
      --ytmusic-color-black3: {surface};
      --ytmusic-color-white1: #ebeee7;
      --ytmusic-color-white2: #bac0b7;
      --ytmusic-color-white3: #929b8d;
      --ytmusic-color-light1: {accent};
      --ytmusic-color-light2: {accent};
      --ytmusic-color-light3: {accent};
      --yt-spec-base-background: #121512;
      --yt-spec-raised-background: {surface};
      --yt-spec-menu-background: {surface};
      --yt-spec-call-to-action: {accent};
      --yt-spec-themed-blue: {accent};
      --paper-slider-active-color: {accent};
      --paper-slider-knob-color: {accent};
      --paper-progress-active-color: {accent};
    }}
    html, body, ytmusic-app {{ background: #121512 !important; }}
    ytmusic-nav-bar, ytmusic-player-bar, ytmusic-guide-renderer {{ background: {surface} !important; }}
    ytmusic-chip-cloud-chip-renderer[selected] {{ background: {accent} !important; color: #162012 !important; }}
    ytmusic-chip-cloud-chip-renderer[selected] yt-formatted-string {{ color: #162012 !important; }}
    tp-yt-paper-slider {{ --paper-slider-active-color:{accent}; --paper-slider-knob-color:{accent}; }}
    ytmusic-player-bar #progress-bar {{ --paper-progress-active-color:{accent}; }}
    '''
    return """(() => {
      if(location.hostname!=='music.youtube.com')return;
      let style=document.getElementById('aural-music-theme');
      if(!style){style=document.createElement('style');style.id='aural-music-theme';document.documentElement.append(style)}
      style.textContent=CSS;
    })()""".replace('CSS',json.dumps(css))
