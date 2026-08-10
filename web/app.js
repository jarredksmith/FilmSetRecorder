(() => {
  const $ = (id) => document.getElementById(id);
  const overlay = $('pairOverlay');
  const toast = $('toast');
  const phonePlayer = $('phonePlayer');
  const waveCanvas = $('phoneWaveform');
  const waveCtx = waveCanvas.getContext('2d');
  let paired=false, busy=false, lastState=null, toastTimer=null;
  let takes=[], selectedTakeId='', waveform=null, notesDirty=false, lastWaveformTakeId='';

  function showToast(m){ toast.textContent=m; toast.classList.add('show'); clearTimeout(toastTimer); toastTimer=setTimeout(()=>toast.classList.remove('show'),1700); }
  function formatClock(seconds){ const ms=Math.max(0,Math.floor((Number(seconds)||0)*1000)),h=Math.floor(ms/3600000),m=Math.floor((ms%3600000)/60000),s=Math.floor((ms%60000)/1000),r=ms%1000; return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}.${String(r).padStart(3,'0')}`; }
  function shortDuration(seconds){ const n=Math.max(0,Math.round(Number(seconds)||0)),m=Math.floor(n/60),s=n%60; return `${m}:${String(s).padStart(2,'0')}`; }
  function dbPercent(db){ const v=Math.max(-60,Math.min(0,Number(db)||-80)); return ((v+60)/60)*100; }
  function setConnection(mode,text){ const p=$('connectionPill'); p.classList.remove('ready','offline'); if(mode)p.classList.add(mode); $('connectionText').textContent=text; }
  function escapeHtml(v){const d=document.createElement('div');d.textContent=String(v??'');return d.innerHTML;}

  async function jsonFetch(url,options={}){
    const response=await fetch(url,{...options,cache:'no-store',credentials:'same-origin',headers:{'Content-Type':'application/json',...(options.headers||{})}});
    let body={}; try{body=await response.json();}catch(_){}
    if(!response.ok){const e=new Error(body.error||`HTTP ${response.status}`);e.status=response.status;throw e;}
    return body;
  }
  async function command(command,extra={}){if(!paired)return;try{await jsonFetch('/api/command',{method:'POST',body:JSON.stringify({command,request_id:`${Date.now()}-${Math.random()}`,...extra})});}catch(e){if(e.status===401)requirePairing();else showToast(e.message||'Command failed');}}

  function buildMeters(state){
    const w=$('meters'),names=state.tracks||[],meters=state.meters||[],armed=state.armed||[],count=Math.max(names.length,meters.length,1);
    if(w.children.length!==count){w.innerHTML='';for(let i=0;i<count;i++){const row=document.createElement('div');row.className='meter-row';row.innerHTML=`<div class="meter-name"><small>CH ${String(i+1).padStart(2,'0')}</small><b data-name></b></div><div class="meter-track"><div class="meter-fill" data-fill></div></div><div class="meter-db" data-db>−∞</div>`;w.appendChild(row);}}
    [...w.children].forEach((row,i)=>{const db=Number(meters[i]??-80);row.querySelector('[data-name]').textContent=names[i]||`Track ${i+1}`;row.querySelector('[data-fill]').style.width=`${dbPercent(db)}%`;row.querySelector('[data-fill]').style.opacity=armed[i]===false?'.25':'1';row.querySelector('[data-db]').textContent=db<=-79?'−∞':db.toFixed(1);});
  }

  function sourceLabel(index,count){if(count===2)return `Input ${index+1} · ${index===0?'L':'R'}`;return `Input ${index+1}`;}
  function buildMixer(state){
    const root=$('mixerRows'), names=state.tracks||[], trims=state.trims||[], sources=state.sources||[], sourceCount=Math.max(1,Number(state.source_count)||1);
    const count=Math.max(1,names.length);
    if(root.children.length!==count){
      root.innerHTML='';
      for(let i=0;i<count;i++){
        const row=document.createElement('div'); row.className='mixer-row'; row.dataset.track=i;
        row.innerHTML=`<div class="mixer-name" data-mix-name></div><select class="source-select" data-source></select><div class="trim-wrap"><input type="range" class="trim-slider" data-trim min="-24" max="24" step="0.5" value="0"><span data-trim-value>0.0 dB</span></div>`;
        const select=row.querySelector('[data-source]');
        select.addEventListener('change',()=>command('set_track_source',{track:i,source:Number(select.value)}));
        const slider=row.querySelector('[data-trim]'), value=row.querySelector('[data-trim-value]');
        slider.addEventListener('input',()=>{value.textContent=`${Number(slider.value)>=0?'+':''}${Number(slider.value).toFixed(1)} dB`;});
        slider.addEventListener('change',()=>command('set_trim',{track:i,db:Number(slider.value)}));
        root.appendChild(row);
      }
    }
    [...root.children].forEach((row,i)=>{
      row.querySelector('[data-mix-name]').textContent=names[i]||`Track ${i+1}`;
      const select=row.querySelector('[data-source]');
      const currentSource=Number(sources[i]??i);
      if(select.options.length!==sourceCount){select.innerHTML='';for(let n=0;n<sourceCount;n++){const opt=document.createElement('option');opt.value=String(n);opt.textContent=sourceLabel(n,sourceCount);select.appendChild(opt);}}
      if(document.activeElement!==select)select.value=String(Math.min(sourceCount-1,Math.max(0,currentSource)));
      select.disabled=!!state.recording;
      const slider=row.querySelector('[data-trim]'), value=row.querySelector('[data-trim-value]'), trim=Number(trims[i]??0);
      if(document.activeElement!==slider)slider.value=String(trim);
      value.textContent=`${trim>=0?'+':''}${trim.toFixed(1)} dB`;
    });
  }

  function render(state){
    lastState=state; $('projectName').textContent=state.project||'FilmSet Recorder'; $('roll').textContent=state.roll||'—'; $('scene').textContent=state.scene||'—'; $('take').textContent=String(state.take??'—').padStart(3,'0'); $('clock').textContent=formatClock(state.elapsed); $('xruns').textContent=state.xruns??0; $('drops').textContent=state.dropped_blocks??0; $('audioState').textContent=state.audio_ready?'READY':'OFFLINE'; $('diskState').textContent=state.disk_display||'—';
    const circle=!!state.circle; $('circleButton').classList.toggle('active',circle); $('circleTop').classList.toggle('active',circle); const label=$('stateLabel'); label.classList.remove('recording','playing'); $('recordButton').classList.toggle('recording',!!state.recording); if(state.recording){label.textContent='● RECORDING';label.classList.add('recording');}else if(state.playing){label.textContent='▶ PLAYING ON RECORDER';label.classList.add('playing');}else{label.textContent=state.audio_ready?'READY':'AUDIO OFFLINE';}
    buildMeters(state); buildMixer(state); if(state.playing) drawWaveform();
  }

  async function pair(){const pin=$('pinInput').value.replace(/\D/g,'').slice(0,6);$('pinInput').value=pin;if(pin.length!==6){$('pairError').textContent='Enter all six digits.';return;}$('pairError').textContent='';try{await jsonFetch('/api/pair',{method:'POST',body:JSON.stringify({pin})});paired=true;overlay.classList.add('hidden');showToast('Remote paired');await Promise.all([poll(),loadTakes()]);}catch(e){$('pairError').textContent=e.message||'Pairing failed.';}}
  function requirePairing(){paired=false;overlay.classList.remove('hidden');setConnection('offline','PAIRING');}
  async function poll(){if(busy)return;busy=true;try{const state=await jsonFetch('/api/status');paired=true;overlay.classList.add('hidden');setConnection('ready','CONNECTED');render(state);}catch(e){if(e.status===401)requirePairing();else setConnection('offline','OFFLINE');}finally{busy=false;}}

  function selectedTake(){return takes.find(t=>t.id===selectedTakeId);}
  function renderTakes(){
    const list=$('takeList');
    if(!takes.length){list.innerHTML='<div class="empty">No completed takes yet.</div>';selectedTakeId='';}
    else{list.innerHTML='';takes.forEach(t=>{const b=document.createElement('button');b.className='take-item'+(t.id===selectedTakeId?' selected':'');b.innerHTML=`<div class="take-star ${t.circle?'circle':''}">${t.circle?'★':'○'}</div><div class="take-main"><div class="take-title">${escapeHtml(t.roll||'')} · ${escapeHtml(t.scene||'')} · T${String(t.take||0).padStart(3,'0')}</div><div class="take-sub">${escapeHtml(t.file||'')}${t.notes?' · '+escapeHtml(t.notes):''}</div></div><div class="take-duration">${shortDuration(t.duration_seconds)}</div>`;b.addEventListener('click',()=>selectTake(t.id));list.appendChild(b);});}
    const enabled=!!selectedTakeId, locked=!!lastState?.recording; $('playSelectedRecorder').disabled=!enabled||locked; $('listenSelectedPhone').disabled=!enabled||locked; $('saveTakeNotes').disabled=!enabled||locked; $('takeNotes').disabled=locked;
    const t=selectedTake(); if(!notesDirty && document.activeElement!==$('takeNotes')) $('takeNotes').value=t?.notes||'';
  }
  async function selectTake(id){const changed=id!==selectedTakeId;selectedTakeId=id;notesDirty=false;renderTakes();if(changed||lastWaveformTakeId!==id)await loadWaveform();}
  async function loadTakes(){if(!paired)return;try{const data=await jsonFetch('/api/takes');const old=selectedTakeId;takes=data.takes||[];if(old&&takes.some(t=>t.id===old))selectedTakeId=old;else if(takes.length)selectedTakeId=takes[0].id;else selectedTakeId='';renderTakes();if(selectedTakeId&&lastWaveformTakeId!==selectedTakeId)await loadWaveform();}catch(e){if(e.status===401)requirePairing();}}

  function sizeWaveCanvas(){const ratio=window.devicePixelRatio||1;const r=waveCanvas.getBoundingClientRect();const w=Math.max(10,Math.floor(r.width*ratio)),h=Math.max(10,Math.floor(104*ratio));if(waveCanvas.width!==w||waveCanvas.height!==h){waveCanvas.width=w;waveCanvas.height=h;}return {w,h,ratio};}
  function drawWaveform(){
    const {w,h}=sizeWaveCanvas(); waveCtx.clearRect(0,0,w,h); waveCtx.fillStyle='#07131f'; waveCtx.fillRect(0,0,w,h); waveCtx.strokeStyle='#163149'; waveCtx.lineWidth=1; waveCtx.beginPath(); waveCtx.moveTo(0,h/2); waveCtx.lineTo(w,h/2); waveCtx.stroke();
    if(!waveform||!waveform.mins?.length){waveCtx.fillStyle='#6f859a';waveCtx.font=`${10*(window.devicePixelRatio||1)}px sans-serif`;waveCtx.textAlign='center';waveCtx.fillText(selectedTakeId?'Loading waveform…':'Select a take',w/2,h/2+4);return;}
    const mins=waveform.mins,maxs=waveform.maxs,count=Math.min(mins.length,maxs.length);waveCtx.strokeStyle='#36a8ff';waveCtx.lineWidth=Math.max(1,window.devicePixelRatio||1);waveCtx.beginPath();const half=h*.42,mid=h/2;for(let i=0;i<count;i++){const x=(i/(Math.max(1,count-1)))*w;waveCtx.moveTo(x,mid-Math.max(-1,Math.min(1,maxs[i]))*half);waveCtx.lineTo(x,mid-Math.max(-1,Math.min(1,mins[i]))*half);}waveCtx.stroke();
    const phoneActive=!phonePlayer.paused && !!phonePlayer.src; const remoteActive=!!lastState?.playing && lastState?.playback_file_id===selectedTakeId; const duration=phoneActive?(Number(phonePlayer.duration)||Number(waveform.duration_seconds)||0):(remoteActive?(Number(lastState.playback_duration)||Number(waveform.duration_seconds)||0):(Number(waveform.duration_seconds)||0)); const position=phoneActive?(Number(phonePlayer.currentTime)||0):(remoteActive?(Number(lastState.playback_elapsed)||0):0);if(duration>0){const x=Math.max(0,Math.min(w,position/duration*w));waveCtx.strokeStyle='#fff';waveCtx.lineWidth=2*(window.devicePixelRatio||1);waveCtx.beginPath();waveCtx.moveTo(x,0);waveCtx.lineTo(x,h);waveCtx.stroke();}
    $('waveTime').textContent=`${shortDuration(position)} / ${shortDuration(duration)}`;
  }

  function scrubPhoneWaveform(event){
    if(!waveform||!selectedTakeId)return;
    const rect=waveCanvas.getBoundingClientRect();
    const clientX=event.touches?.[0]?.clientX ?? event.clientX;
    const frac=Math.max(0,Math.min(1,(clientX-rect.left)/Math.max(1,rect.width)));
    const duration=Number(phonePlayer.duration)||Number(waveform.duration_seconds)||0;
    if(duration<=0)return;
    if(!phonePlayer.src){
      const t=selectedTake(); if(!t)return;
      phonePlayer.src=`/api/audio?id=${encodeURIComponent(t.id)}&v=${Date.now()}`;
    }
    phonePlayer.currentTime=frac*duration;
    drawWaveform();
  }

  async function loadWaveform(){waveform=null;lastWaveformTakeId=selectedTakeId;drawWaveform();if(!selectedTakeId||lastState?.recording)return;try{waveform=await jsonFetch(`/api/waveform?id=${encodeURIComponent(selectedTakeId)}`);drawWaveform();}catch(_){waveform=null;drawWaveform();}}

  async function listenOnPhone(){const t=selectedTake();if(!t)return;phonePlayer.pause();phonePlayer.currentTime=0;phonePlayer.src=`/api/audio?id=${encodeURIComponent(t.id)}&v=${Date.now()}`;$('phoneNowPlaying').textContent=`Loading ${t.file}…`;try{await phonePlayer.play();$('phoneNowPlaying').textContent=`Listening on phone: ${t.file}`;}catch(_){$('phoneNowPlaying').textContent=`Tap the audio play control for ${t.file}`;}}
  async function saveTakeNotes(){if(!selectedTakeId)return;await command('set_take_notes',{take_id:selectedTakeId,notes:$('takeNotes').value});notesDirty=false;showToast('Take notes saved');setTimeout(loadTakes,300);}

  $('pairButton').addEventListener('click',pair); $('pinInput').addEventListener('keydown',e=>{if(e.key==='Enter')pair();}); $('pinInput').addEventListener('input',e=>{e.target.value=e.target.value.replace(/\D/g,'').slice(0,6);});
  $('recordButton').addEventListener('click',()=>command('record')); $('stopButton').addEventListener('click',()=>command('stop')); $('playButton').addEventListener('click',()=>command('play')); $('nextButton').addEventListener('click',()=>command('next_take')); $('circleButton').addEventListener('click',()=>command('toggle_circle')); $('circleTop').addEventListener('click',()=>command('toggle_circle'));
  $('takeNotes').addEventListener('input',()=>{notesDirty=true;}); $('refreshTakes').addEventListener('click',loadTakes); $('playSelectedRecorder').addEventListener('click',()=>{if(selectedTakeId)command('play_take',{take_id:selectedTakeId});}); $('listenSelectedPhone').addEventListener('click',listenOnPhone); $('saveTakeNotes').addEventListener('click',saveTakeNotes);
  $('sceneBox').addEventListener('click',()=>{if(!lastState||lastState.recording)return;const v=prompt('Scene',lastState.scene||'');if(v!==null&&v.trim())command('set_scene',{scene:v.trim()});}); $('takeBox').addEventListener('click',()=>{if(!lastState||lastState.recording)return;const v=prompt('Take number',lastState.take||1),n=Number.parseInt(v,10);if(Number.isFinite(n)&&n>0)command('set_take',{take:n});});
  $('unpairButton').addEventListener('click',async()=>{try{await jsonFetch('/api/unpair',{method:'POST',body:'{}'});}catch(_){}requirePairing();});
  waveCanvas.addEventListener('click',scrubPhoneWaveform); waveCanvas.addEventListener('touchstart',e=>{scrubPhoneWaveform(e);e.preventDefault();},{passive:false});
  phonePlayer.addEventListener('timeupdate',drawWaveform); phonePlayer.addEventListener('loadedmetadata',drawWaveform); phonePlayer.addEventListener('ended',()=>{$('phoneNowPlaying').textContent='Phone playback finished.';drawWaveform();}); window.addEventListener('resize',drawWaveform);
  (async()=>{const match=window.location.hash.match(/(?:^#|&)pin=(\d{6})(?:&|$)/);if(match){$('pinInput').value=match[1];history.replaceState(null,'',window.location.pathname+window.location.search);await pair();}try{const info=await jsonFetch('/api/info');$('projectName').textContent=info.project||'Remote Control';}catch(_){}await poll();if(paired)await loadTakes();})();
  setInterval(poll,200); setInterval(()=>{if(paired)loadTakes();},5000);
})();
