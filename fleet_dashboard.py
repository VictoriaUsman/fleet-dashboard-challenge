import csv
import json
import os
from datetime import datetime

STATUS_CONFIG = {
    'active':      {'color': '#22c55e', 'label': 'Active'},
    'idle':        {'color': '#f59e0b', 'label': 'Idle'},
    'low_battery': {'color': '#ef4444', 'label': 'Low Battery'},
    'offline':     {'color': '#6b7280', 'label': 'Offline'},
    'maintenance': {'color': '#3b82f6', 'label': 'Maintenance'},
}
UNKNOWN_STATUS = {'color': '#a855f7', 'label': 'Unknown'}

SUMMARY_ORDER = ['active', 'idle', 'low_battery', 'offline', 'maintenance']


def _parse_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_battery(val):
    v = _parse_float(val)
    if v is None:
        return None
    return max(0, min(100, int(v)))


def _time_ago(last_seen_str, now):
    try:
        ts = datetime.strptime(last_seen_str, '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return 'Unknown'
    secs = (now - ts).total_seconds()
    if secs < 0:
        return 'Future'
    if secs < 60:
        return f'{int(secs)}s ago'
    if secs < 3600:
        return f'{int(secs // 60)}m ago'
    if secs < 86400:
        return f'{int(secs // 3600)}h ago'
    return f'{int(secs // 86400)}d ago'


def read_fleet(csv_path):
    devices = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            did = (row.get('device_id') or '').strip()
            name = (row.get('name') or '').strip() or did
            status = (row.get('status') or '').strip().lower()
            battery = _parse_battery(row.get('battery_pct'))
            lat = _parse_float(row.get('lat'))
            lon = _parse_float(row.get('lon'))
            last_seen = (row.get('last_seen') or '').strip()
            location = (row.get('location') or '').strip()
            devices.append({
                'device_id': did,
                'name': name,
                'status': status,
                'battery': battery,
                'lat': lat,
                'lon': lon,
                'last_seen': last_seen,
                'location': location,
            })
    return devices


def build_html(devices, now):
    # ── summary counts ──────────────────────────────────────────────────────────
    counts = {}
    for d in devices:
        counts[d['status']] = counts.get(d['status'], 0) + 1
    total = len(devices)

    summary_cards_html = ''
    for st in SUMMARY_ORDER:
        cfg = STATUS_CONFIG[st]
        n = counts.get(st, 0)
        summary_cards_html += (
            f'<div class="summary-card" onclick="filterByStatus(\'{st}\')">'
            f'<div class="summary-count" style="color:{cfg["color"]}">{n}</div>'
            f'<div class="summary-label">{cfg["label"]}</div>'
            f'</div>'
        )
    # unknown statuses
    unknown_n = sum(v for k, v in counts.items() if k not in STATUS_CONFIG)
    if unknown_n:
        summary_cards_html += (
            f'<div class="summary-card">'
            f'<div class="summary-count" style="color:{UNKNOWN_STATUS["color"]}">{unknown_n}</div>'
            f'<div class="summary-label">Unknown</div>'
            f'</div>'
        )

    # ── map markers (valid coords only) ────────────────────────────────────────
    markers = []
    for d in devices:
        if d['lat'] is None or d['lon'] is None:
            continue
        cfg = STATUS_CONFIG.get(d['status'], UNKNOWN_STATUS)
        bat_str = f"{d['battery']}%" if d['battery'] is not None else 'N/A'
        markers.append({
            'id': d['device_id'],
            'name': d['name'],
            'lat': d['lat'],
            'lon': d['lon'],
            'status': d['status'],
            'color': cfg['color'],
            'label': cfg['label'],
            'battery': bat_str,
            'time_ago': _time_ago(d['last_seen'], now),
            'location': d['location'],
        })

    # ── device table rows ───────────────────────────────────────────────────────
    rows_html = ''
    for d in devices:
        cfg = STATUS_CONFIG.get(d['status'], UNKNOWN_STATUS)
        bat = d['battery']
        bat_str = f"{bat}%" if bat is not None else 'N/A'
        if bat is None:
            bar_color, bar_w = '#6b7280', 0
        elif bat <= 20:
            bar_color, bar_w = '#ef4444', bat
        elif bat <= 50:
            bar_color, bar_w = '#f59e0b', bat
        else:
            bar_color, bar_w = '#22c55e', bat
        ago = _time_ago(d['last_seen'], now)
        lat_attr = f'data-lat="{d["lat"]}"' if d['lat'] is not None else ''
        lon_attr = f'data-lon="{d["lon"]}"' if d['lon'] is not None else ''
        rows_html += (
            f'<tr class="drow" data-status="{d["status"]}" {lat_attr} {lon_attr}'
            f' onclick="focusDevice(this)">'
            f'<td><span class="did">{d["device_id"]}</span>'
            f'<br><span class="dname">{d["name"]}</span></td>'
            f'<td><span class="sbadge" style="background:{cfg["color"]}22;'
            f'color:{cfg["color"]};border:1px solid {cfg["color"]}44">'
            f'{cfg["label"]}</span></td>'
            f'<td><div class="batbox">'
            f'<div class="batbar"><div class="batfill" style="width:{bar_w}%;background:{bar_color}"></div></div>'
            f'<span class="battxt">{bat_str}</span></div></td>'
            f'<td class="ago">{ago}</td>'
            f'<td class="loc">{d["location"] or "—"}</td>'
            f'</tr>'
        )

    generated = now.strftime('%d %b %Y %H:%M UTC')
    markers_json = json.dumps(markers, ensure_ascii=False)

    # ── HTML template (uses __SLOTS__ to avoid f-string brace conflicts) ────────
    template = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fleet Dashboard – SolidGPS</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0d1117;color:#e2e8f0;height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{background:#161b27;border-bottom:1px solid #21293d;padding:12px 20px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.logo{font-size:17px;font-weight:700;color:#fff;letter-spacing:-.3px}.logo span{color:#3b82f6}
.gen{font-size:12px;color:#566078}
.sumbar{background:#161b27;border-bottom:1px solid #21293d;padding:10px 20px;display:flex;gap:8px;align-items:center;flex-shrink:0;flex-wrap:wrap}
.summary-card{background:#0d1117;border:1px solid #21293d;border-radius:8px;padding:8px 14px;cursor:pointer;transition:border-color .2s;display:flex;align-items:center;gap:10px}
.summary-card:hover{border-color:#3b82f6}.summary-card.sel{border-color:#3b82f6;background:#1e3a5f1a}
.summary-count{font-size:22px;font-weight:700;line-height:1}
.summary-label{font-size:11px;color:#8899aa;text-transform:uppercase;letter-spacing:.5px}
.totbadge{margin-left:auto;background:#1e2535;border-radius:6px;padding:6px 14px;font-size:13px;color:#8899aa}
.totbadge strong{color:#e2e8f0}
.main{display:flex;flex:1;overflow:hidden}
.panel{width:530px;flex-shrink:0;background:#161b27;display:flex;flex-direction:column;border-right:1px solid #21293d}
.ph{padding:10px 14px;border-bottom:1px solid #21293d;display:flex;align-items:center;gap:8px;flex-shrink:0}
.ptitle{font-size:11px;font-weight:600;color:#8899aa;text-transform:uppercase;letter-spacing:.5px}
.srch{flex:1;background:#0d1117;border:1px solid #21293d;border-radius:6px;padding:6px 10px;color:#e2e8f0;font-size:13px;outline:none}
.srch:focus{border-color:#3b82f6}
.clr{font-size:11px;color:#3b82f6;cursor:pointer;white-space:nowrap}.clr:hover{text-decoration:underline}
.tc{overflow-y:auto;flex:1}
table{width:100%;border-collapse:collapse;font-size:13px}
thead th{background:#0d1117;color:#566078;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.5px;padding:8px 12px;text-align:left;border-bottom:1px solid #21293d;position:sticky;top:0;z-index:1}
tbody tr{border-bottom:1px solid #1a2030;cursor:pointer;transition:background .12s}
tbody tr:hover{background:#1e2535}
tbody tr.hl{background:#1e3a5f33}
td{padding:9px 12px;vertical-align:middle}
.did{font-size:11px;color:#566078;font-family:monospace}
.dname{font-weight:500;color:#e2e8f0}
.sbadge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;white-space:nowrap}
.batbox{display:flex;align-items:center;gap:6px}
.batbar{width:44px;height:5px;background:#21293d;border-radius:3px;overflow:hidden;flex-shrink:0}
.batfill{height:100%;border-radius:3px}
.battxt{font-size:12px;color:#8899aa;min-width:32px}
.ago{color:#8899aa;font-size:12px;white-space:nowrap}
.loc{color:#8899aa;font-size:12px}
.map{flex:1;position:relative}
#map{width:100%;height:100%}
.nores{padding:40px;text-align:center;color:#566078;font-size:14px}
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:#0d1117}
::-webkit-scrollbar-thumb{background:#21293d;border-radius:3px}
</style>
</head>
<body>
<header>
  <div class="logo">Solid<span>GPS</span> Fleet Dashboard</div>
  <div class="gen">__GENERATED__ &nbsp;·&nbsp; __TOTAL__ devices</div>
</header>
<div class="sumbar">
  __SUMMARY_CARDS__
  <div class="totbadge">Total: <strong>__TOTAL__</strong></div>
</div>
<div class="main">
  <div class="panel">
    <div class="ph">
      <span class="ptitle">Devices</span>
      <input class="srch" type="text" placeholder="Search name, ID, location…" oninput="doFilter(this.value)">
      <span class="clr" onclick="clearAll()">Clear</span>
    </div>
    <div class="tc">
      <table>
        <thead><tr><th>Device</th><th>Status</th><th>Battery</th><th>Last Seen</th><th>Location</th></tr></thead>
        <tbody id="tb">__ROWS__</tbody>
      </table>
      <div id="nores" class="nores" style="display:none">No devices match.</div>
    </div>
  </div>
  <div class="map"><div id="map"></div></div>
</div>
<script>
var MD = __MARKERS_JSON__;
var map = L.map('map').setView([-27,133],4);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
  attribution:'© OpenStreetMap contributors',maxZoom:18
}).addTo(map);

var LM = {};
function mkIcon(c){
  var s='<svg xmlns="http://www.w3.org/2000/svg" width="26" height="34" viewBox="0 0 26 34">'+
    '<path d="M13 0C5.82 0 0 5.82 0 13c0 9.1 13 21 13 21s13-11.9 13-21C26 5.82 20.18 0 13 0z" fill="'+c+'" stroke="#fff" stroke-width="2"/>'+
    '<circle cx="13" cy="13" r="5" fill="#fff" fill-opacity=".8"/>'+
    '</svg>';
  return L.divIcon({html:s,className:'',iconSize:[26,34],iconAnchor:[13,34],popupAnchor:[0,-34]});
}
MD.forEach(function(d){
  var m=L.marker([d.lat,d.lon],{icon:mkIcon(d.color)}).addTo(map);
  m.bindPopup(
    '<div style="font-family:-apple-system,sans-serif;min-width:190px">'+
    '<div style="font-weight:700;font-size:14px;margin-bottom:3px">'+d.name+'</div>'+
    '<div style="font-size:11px;color:#888;margin-bottom:8px">'+d.id+'</div>'+
    '<span style="background:'+d.color+'22;color:'+d.color+';border:1px solid '+d.color+'44;'+
    'padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">'+d.label+'</span>'+
    '<table style="width:100%;margin-top:8px;font-size:12px;border-collapse:collapse">'+
    '<tr><td style="color:#888;padding:2px 4px 2px 0">Battery</td><td style="font-weight:500">'+d.battery+'</td></tr>'+
    '<tr><td style="color:#888;padding:2px 4px 2px 0">Last seen</td><td style="font-weight:500">'+d.time_ago+'</td></tr>'+
    '<tr><td style="color:#888;padding:2px 4px 2px 0">Location</td><td style="font-weight:500">'+d.location+'</td></tr>'+
    '</table></div>'
  );
  LM[d.id]=m;
});

var activeStatus=null;
function doFilter(q){
  var rows=document.querySelectorAll('#tb tr');
  var vis=0;q=q.toLowerCase();
  rows.forEach(function(r){
    var sm=!activeStatus||r.dataset.status===activeStatus;
    var qm=!q||r.textContent.toLowerCase().includes(q);
    r.style.display=(sm&&qm)?'':'none';
    if(sm&&qm)vis++;
  });
  document.getElementById('nores').style.display=vis?'none':'';
}
function filterByStatus(s){
  activeStatus=(activeStatus===s)?null:s;
  document.querySelectorAll('.summary-card').forEach(function(c){c.classList.remove('sel')});
  if(activeStatus){
    var cards=document.querySelectorAll('.summary-card');
    var order=['active','idle','low_battery','offline','maintenance'];
    var idx=order.indexOf(s);
    if(idx>=0&&cards[idx])cards[idx].classList.add('sel');
  }
  doFilter(document.querySelector('.srch').value);
}
function clearAll(){
  activeStatus=null;
  document.querySelector('.srch').value='';
  document.querySelectorAll('.summary-card').forEach(function(c){c.classList.remove('sel')});
  document.querySelectorAll('#tb tr').forEach(function(r){r.style.display=''});
  document.getElementById('nores').style.display='none';
}
function focusDevice(row){
  document.querySelectorAll('#tb tr').forEach(function(r){r.classList.remove('hl')});
  row.classList.add('hl');
  var lat=row.dataset.lat,lon=row.dataset.lon;
  var did=row.querySelector('.did').textContent;
  if(lat&&lon){map.setView([parseFloat(lat),parseFloat(lon)],13,{animate:true});}
  if(LM[did])LM[did].openPopup();
}
</script>
</body>
</html>'''

    html = (template
            .replace('__GENERATED__', generated)
            .replace('__TOTAL__', str(total))
            .replace('__SUMMARY_CARDS__', summary_cards_html)
            .replace('__ROWS__', rows_html)
            .replace('__MARKERS_JSON__', markers_json))
    return html


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'fleet_status.csv')
    out_path = os.path.join(script_dir, 'fleet_dashboard.html')

    now = datetime.utcnow()
    devices = read_fleet(csv_path)
    html = build_html(devices, now)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'Dashboard written to: {out_path}')
    print(f'Devices processed:    {len(devices)}')
    invalid = [d['device_id'] for d in devices if d['lat'] is None or d['lon'] is None]
    if invalid:
        print(f'Skipped from map (bad coords): {", ".join(invalid)}')


if __name__ == '__main__':
    main()
