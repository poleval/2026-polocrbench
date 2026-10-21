const $ = id => document.getElementById(id);
const state = {docs:[], filtered:[], current:null, second:null, page:1, pageB:1, filter:'scanned', mode:'text', textToken:0, zoom:100,queue:[],annotation:null,annotationToken:0};
const labels = {scanned:'Skan',digital:'Cyfrowy',mixed:'Mieszany',uncertain:'Niepewny'};
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm = value => value.toLocaleLowerCase('pl').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ł/g,'l');
function filterDocs(){
 const q=norm($('search').value), org=$('organization').value;
 const workset=$('workset').value;const queued=new Set(filteredQueue().map(r=>r.document_id));
 state.filtered=state.docs.filter(d=>(!workset||queued.has(d.id))&&(state.filter==='all'||d.label===state.filter)&&(!$('needsOcr').checked||d.ocr_needed>0)&&(!org||d.organization===org)&&norm([d.filename,d.title,d.organization,d.topic].join(' ')).includes(q));
 const sort=$('sort').value;
 state.filtered.sort((a,b)=>sort==='pages'?b.pages-a.pages:sort==='ocr'?b.ocr_needed-a.ocr_needed:a.filename.localeCompare(b.filename));
 $('count').textContent=state.filtered.length;
 $('resultInfo').textContent=`${state.filtered.length} wyników`;
 $('list').innerHTML=state.filtered.length?state.filtered.map(d=>`<button class="doc ${state.current?.id===d.id?'active':''}" data-id="${esc(d.id)}"><div class="doc-top"><span>${esc(d.organization||'Dokument')}</span><span>${esc(d.date)}</span></div><div class="doc-title">${esc(d.title)}</div><div class="doc-file">${esc(d.filename)}</div><div class="doc-bottom"><span class="badge ${d.label==='digital'?'digital':''}">${labels[d.label]}</span><span>${d.pages} str.</span>${d.ocr_needed?`<span class="badge warn">${d.ocr_needed} str. bez tekstu</span>`:`<span>${d.ocr_pages?'Ma warstwę tekstu':'Tekst cyfrowy'}</span>`}</div></button>`).join(''):'<div class="empty">Brak dokumentów dla tych filtrów. Zmień wyszukiwanie lub wyłącz filtr warstwy tekstu.</div>';
 if(state.filtered.length&&!state.filtered.some(d=>d.id===state.current?.id))selectDoc(state.filtered[0].id,false);
}
function selectDoc(id,refresh=true){
 const doc=state.docs.find(d=>d.id===id);if(!doc)return;
 state.current=doc;state.page=queueForDocument(doc.id)[0]?.page||1;
 $('detailTitle').textContent=doc.title;
 $('detailMeta').textContent=`${doc.organization||'Dokument'} · ${doc.date} · ${labels[doc.label]}`;
 $('detailCounts').textContent=`${doc.pages} stron · ${doc.scan_pages} stron rastrowych · ${doc.ocr_pages} z tekstem · ${doc.ocr_needed} bez tekstu · pewność modelu ${(doc.confidence*100).toFixed(1)}%`;
 $('openPdf').href='/files/'+doc.path.split('/').map(encodeURIComponent).join('/');
 $('page').max=doc.pages;$('pageTotal').textContent=`/ ${doc.pages}`;
 const url=new URL(location);url.searchParams.set('doc',doc.id);history.replaceState(null,'',url);
 if(refresh)filterDocs();
 else for(const button of $('list').querySelectorAll('.doc'))button.classList.toggle('active',button.dataset.id===id);
 renderPrimary();
}
function updatePager(suffix,page,total){$('page'+suffix).value=page;$('prev'+suffix).disabled=page<=1;$('next'+suffix).disabled=page>=total;}
function renderPrimary(){
 const d=state.current;if(!d)return;updatePager('',state.page,d.pages);
 const metric=d.page_metrics[state.page-1];
 $('pageEvidence').textContent=`Strona ${state.page} · raster ${(metric.high_res_raster_coverage*100).toFixed(0)}% · ${metric.text_chars.toLocaleString('pl')} znaków tekstu${metric.hidden_text_chars?' · ukryta warstwa OCR':''}${metric.scan_evidence&&metric.text_chars<40?' · kandydat do OCR':''}`;
 $('primaryImage').src=`/api/page?id=${encodeURIComponent(d.id)}&page=${state.page}`;
 $('primaryImage').style.width=state.zoom+'%';$('primaryImage').closest('.image-scroll').scrollTop=0;
 loadText();
 if(state.mode==='annotate')loadAnnotation();
}
async function loadText(){
 if(!state.current)return;const token=++state.textToken;
 $('textContent').textContent='Wczytywanie tekstu…';
 const publisher=$('textSource').value==='publisher';
 $('textInfo').textContent=publisher?`Cały dokument · ${state.current.text_source||'tekst dostarczony przez wydawcę'}`:`Tekst wyodrębniony lokalnie · strona ${state.page}`;
 try{const response=await fetch(`/api/text?id=${encodeURIComponent(state.current.id)}&page=${state.page}&source=${publisher?'publisher':'native'}`);if(!response.ok)throw Error('Nie udało się pobrać tekstu.');const {text}=await response.json();if(token!==state.textToken)return;$('textContent').textContent=text.trim()?text:'Brak tekstu na tej stronie PDF. To dobry kandydat do OCR. W trybie „Tekst z datasetu” może być dostępny tekst od wydawcy.';}
 catch(error){if(token===state.textToken)$('textContent').textContent=error.message;}
}
function fillSecond(){
 const q=norm($('compareSearch').value);const choices=state.docs.filter(d=>norm([d.filename,d.title,d.organization].join(' ')).includes(q));
 $('compareSelect').innerHTML=choices.map(d=>`<option value="${esc(d.id)}">${esc(labels[d.label]+' · '+d.filename)}</option>`).join('');
 if(choices.some(d=>d.id===state.second?.id))$('compareSelect').value=state.second.id;
 else{state.second=choices[0]||null;state.pageB=1;}
 renderSecond();
}
function renderSecond(){
 const d=state.second;if(!d){$('secondaryImage').removeAttribute('src');$('pageTotalB').textContent='/ 0';$('prevB').disabled=true;$('nextB').disabled=true;return;}
 $('pageB').max=d.pages;$('pageTotalB').textContent=`/ ${d.pages}`;updatePager('B',state.pageB,d.pages);
 $('secondaryImage').src=`/api/page?id=${encodeURIComponent(d.id)}&page=${state.pageB}`;$('secondaryImage').style.width=state.zoom+'%';$('secondaryImage').closest('.image-scroll').scrollTop=0;
}
function setMode(mode){state.mode=mode;$('textPane').hidden=mode!=='text';$('comparePane').hidden=mode!=='compare';$('annotationPane').hidden=mode!=='annotate';document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));if(mode==='compare'&&!state.second){state.second=state.docs.find(d=>d.id!==state.current?.id&&d.label==='digital')||state.docs[1];fillSecond();}if(mode==='annotate')loadAnnotation();}
function movePage(delta,secondary=false){const d=secondary?state.second:state.current;if(!d)return;const key=secondary?'pageB':'page';state[key]=Math.max(1,Math.min(d.pages,state[key]+delta));secondary?renderSecond():renderPrimary();}
$('list').addEventListener('click',event=>{const button=event.target.closest('[data-id]');if(button)selectDoc(button.dataset.id);});
for(const id of ['search','organization','needsOcr','sort','workset','queueStage'])$(id).addEventListener(id==='search'?'input':'change',()=>{if(id==='queueStage'&&$('queueStage').value&&!$('workset').value)$('workset').value='queue';filterDocs();});
document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{state.filter=b.dataset.filter;document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x===b));filterDocs();}));
document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>setMode(b.dataset.mode)));
for(const [suffix,secondary] of [['',false],['B',true]]){
 $('prev'+suffix).onclick=()=>movePage(-1,secondary);$('next'+suffix).onclick=()=>movePage(1,secondary);
 $('page'+suffix).onchange=()=>{const doc=secondary?state.second:state.current;if(!doc)return;const value=Math.round(Number($('page'+suffix).value)||1);state[secondary?'pageB':'page']=Math.max(1,Math.min(doc.pages,value));secondary?renderSecond():renderPrimary();};
}
$('textSource').onchange=loadText;$('compareSearch').oninput=fillSecond;
$('compareSelect').onchange=()=>{state.second=state.docs.find(d=>d.id===$('compareSelect').value);state.pageB=1;renderSecond();};
$('zoom').oninput=()=>{state.zoom=Number($('zoom').value);$('zoomValue').textContent=state.zoom+'%';for(const id of ['primaryImage','secondaryImage'])$(id).style.width=state.zoom+'%';};
$('copyText').onclick=async()=>{try{await navigator.clipboard.writeText($('textContent').textContent);$('copyText').textContent='Skopiowano';setTimeout(()=>$('copyText').textContent='Kopiuj',1500);}catch{$('status').textContent='Zaznacz tekst i skopiuj go skrótem klawiaturowym.';}};
for(const id of ['primaryImage','secondaryImage'])$(id).onerror=()=>{$('status').textContent='Nie udało się wyrenderować strony. Spróbuj zmienić stronę lub otwórz plik PDF.';};
async function init(){
 try{const response=await fetch('/api/documents');if(!response.ok)throw Error('Nie udało się wczytać datasetu.');state.docs=await response.json();
 $('stats').innerHTML=`<span><b>${state.docs.length.toLocaleString('pl')}</b>dokumentów PDF</span><span><b>${state.docs.filter(d=>d.label==='scanned').length}</b>skanów</span><span><b>${state.docs.reduce((n,d)=>n+d.ocr_needed,0)}</b>stron bez tekstu</span>`;
 $('organization').innerHTML+=[...new Set(state.docs.map(d=>d.organization).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'pl')).map(org=>`<option>${esc(org)}</option>`).join('');
 try{state.queue=await(await fetch('/api/queue')).json();}catch{state.queue=[];}
 const requested=new URL(location).searchParams.get('doc');if(requested){state.current=state.docs.find(d=>d.id===requested)||null;if(state.current)state.filter=state.current.label;document.querySelectorAll('[data-filter]').forEach(b=>b.classList.toggle('active',b.dataset.filter===state.filter));}
 filterDocs();if(state.current)selectDoc(state.current.id,false);
 $('status').textContent='Lokalny podgląd · pliki pozostają na tym komputerze · brak wywołań API';
 }catch(error){$('status').textContent=error.message;$('list').innerHTML='<div class="empty">Błąd wczytywania danych. Sprawdź, czy serwer został uruchomiony z scripts/explore_dataset.py.</div>';}
}
function filteredQueue(){const workset=$('workset').value,stage=$('queueStage').value;return state.queue.filter(r=>(!workset||workset==='queue'||r.planned_split===workset)&&(!stage||r.status===stage));}
function queueForDocument(id){if(!$('workset').value)return[];return filteredQueue().filter(r=>r.document_id===id).sort((a,b)=>a.page-b.page);}
const annotationLabels={unstarted:'Nie rozpoczęto',draft:'Szkic',submitted:'Czeka na przegląd 1',reviewed_once:'Czeka na przegląd 2',verified:'Dwa przeglądy zakończone',excluded:'Wykluczono'};
const editorIds=['annotationText','annotationTables','annotationKie','annotationFieldTypes','annotationNote'];
function sampleId(){return state.current?`gm_${state.current.sha256.slice(0,16)}_p${String(state.page).padStart(4,'0')}`:'';}
function storeDraft(){if(!state.annotation||state.annotation.id!==sampleId())return;const draft=Object.fromEntries(editorIds.map(id=>[id,$(id).value]));draft.base_revision=state.annotation.revision;localStorage.setItem('polocr.draft.'+sampleId(),JSON.stringify(draft));$('annotationMessage').textContent='Szkic zachowany w przeglądarce. Kliknij „Zapisz szkic”, aby zapisać go w kolejce.';}
async function loadAnnotation(){
 const token=++state.annotationToken;state.annotation=null;$('annotationMessage').textContent='Wczytywanie anotacji…';
 document.querySelectorAll('[data-action]').forEach(b=>b.disabled=true);
 try{const response=await fetch(`/api/annotation?id=${encodeURIComponent(state.current.id)}&page=${state.page}`);if(!response.ok)throw Error('Nie można wczytać anotacji.');const row=await response.json();if(token!==state.annotationToken)return;state.annotation=row;
 $('annotationText').value=row.text??'';$('annotationTables').value=JSON.stringify(row.tables??null,null,2);$('annotationKie').value=JSON.stringify(row.kie??null,null,2);$('annotationFieldTypes').value=JSON.stringify(row.field_types??{},null,2);$('annotationNote').value='';
 $('annotationStatus').textContent=annotationLabels[row.status]||row.status;$('annotationHistory').textContent=`Wersja ${row.revision} · autor: ${row.annotator||'—'} · przeglądy: ${row.reviews.map(r=>r.actor).join(', ')||'brak'}. ${row.history.at(-1)?.note||''}`;
 $('annotationMessage').textContent='';const draft=JSON.parse(localStorage.getItem('polocr.draft.'+row.id)||'null');if(draft&&draft.base_revision===row.revision){editorIds.forEach(id=>$(id).value=draft[id]??'');$('annotationMessage').textContent='Przywrócono niezapisany szkic z przeglądarki.';}else if(draft)$('annotationMessage').textContent='Istnieje starszy szkic przeglądarki. Wczytano nowszą wersję z serwera.';
 document.querySelectorAll('[data-action]').forEach(b=>b.disabled=false);
 }catch(error){if(token===state.annotationToken)$('annotationMessage').textContent=error.message;}
}
async function annotationAction(action){
 if(!state.annotation||state.annotation.id!==sampleId())return;
 const row=state.annotation,id=state.current.id,page=state.page;
 try{const request={actor:$('actor').value.trim(),action,expected_revision:row.revision,note:$('annotationNote').value};
 if(['save','submit'].includes(action))Object.assign(request,{text:$('annotationText').value,tables:JSON.parse($('annotationTables').value||'null'),kie:JSON.parse($('annotationKie').value||'null'),field_types:JSON.parse($('annotationFieldTypes').value||'{}')});
 document.querySelectorAll('[data-action]').forEach(b=>b.disabled=true);
 const response=await fetch(`/api/annotation?id=${encodeURIComponent(id)}&page=${page}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)});const result=await response.json();if(!response.ok)throw Error(result.error||'Błąd zapisu');
 localStorage.removeItem('polocr.draft.'+row.id);const queued=state.queue.find(q=>q.id===row.id);if(queued){queued.status=result.status;queued.reviews=result.reviews.length;}
 if(sampleId()===row.id){await loadAnnotation();$('annotationMessage').textContent='Zapisano · '+annotationLabels[result.status];}
 }catch(error){$('annotationMessage').textContent=error.message;document.querySelectorAll('[data-action]').forEach(b=>b.disabled=false);}
}
editorIds.forEach(id=>$(id).addEventListener('input',storeDraft));
$('actor').value=localStorage.getItem('polocr.actor')||'';$('actor').oninput=()=>localStorage.setItem('polocr.actor',$('actor').value);
$('loadPreannotation').onclick=()=>{if(!state.annotation)return;if($('annotationText').value.trim()){$('annotationMessage').textContent='Pole tekstu zawiera już anotację. Wyczyść je przed wstawieniem tekstu wstępnego.';return;}$('annotationText').value=state.annotation.preannotation||'';storeDraft();};
document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>annotationAction(b.dataset.action));
$('nextQueued').onclick=()=>{const queue=filteredQueue().filter(r=>r.status!=='verified'&&r.status!=='excluded');if(!queue.length){$('annotationMessage').textContent='Brak kolejnych stron w tej kolejce.';return;}const index=queue.findIndex(r=>r.id===sampleId());const next=queue[(index+1)%queue.length];selectDoc(next.document_id);state.page=next.page;renderPrimary();};
init();
