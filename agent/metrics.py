import platform
import psutil
import datetime
import socket

class Data:

    def __init__(self, server_ip="127.0.0.1"):
        self.server_ip = server_ip
        self.update_data()

    def get_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.server_ip, 1))
            ip = s.getsockname()[0]
            s.close()
            return ip   
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except:
                return "127.0.0.1" 

    def update_system_info(self):
        pc = platform.uname()
        self.system_info = {
            "ip": self.get_ip(),
            "system": pc.system,
            "name": pc.node,
            "release": pc.release,
            "version": pc.version,
            "type": pc.machine
        }

    def update_cpu_info(self):
        self.cpu_info = {
            "load" : psutil.cpu_percent(interval=0.5), 
            "frequency" : psutil.cpu_freq().current if psutil.cpu_freq() else 0.0,
            "avg_load" : psutil.getloadavg()[1] / psutil.cpu_count() * 100,
            "last_start" : datetime.datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }

    def update_memory_info(self):
        v = psutil.virtual_memory()
        s = psutil.swap_memory()

        self.ram_info = {
            "total": v.total,
            "available": v.available,
            "percent": v.percent,
            "used": v.used,
            "free": v.free,
            "active": getattr(v, 'active', 0),
            "inactive": getattr(v, 'inactive', 0),
            "buffers": getattr(v, 'buffers', 0),
            "cached": getattr(v, 'cached', 0),
            "shared": getattr(v, 'shared', 0),
            "slab": getattr(v, 'slab', 0)
        }  

        self.swap_info = {
            "total": s.total,
            "used": s.used,
            "free": s.free,
            "percent": s.percent,
            "sin": s.sin,
            "sout": s.sout
        }

    def update_disk_info(self):
        self.disk_list = []
        for part in psutil.disk_partitions(all=False):
            if 'cdrom' in part.opts or part.fstype == '':
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                self.disk_list.append({
                    "name": part.device,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent":usage.percent
                })
            except:
                continue

    def update_temp_info(self):
        try:
            temps = psutil.sensors_temperatures()
        except:
            temps = {}

        res = {
            "acpitz": 0.0,
            "nvme": 0.0,
            "coretemp": 0.0,
            "nic_adapter": 0.0
        }

        if temps:
            if 'acpitz' in temps: res["acpitz"] = temps['acpitz'][0].current
            if 'nvme' in temps: res["nvme"] = temps['nvme'][0].current
            if 'coretemp' in temps: res["coretemp"] = temps['coretemp'][0].current
            for k in temps:
                if any(x in k.lower() for x in ['eth', 'nic', 'wifi']):
                    res["nic_adapter"] = temps[k][0].current
                    break
        self.temp_info = res

    def update_process_info(self):
        procs = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                info = proc.info
                procs.append({
                    "pid": info['pid'],
                    "process_name": info['name'],
                    "ram_used": info['memory_info'].rss
                })  
            except:
                continue
        self.process_list = sorted(procs, key=lambda x: x['ram_used'], reverse=True)[:15]

    def update_data(self):
        self.update_system_info()
        self.update_cpu_info()
        self.update_memory_info()
        self.update_disk_info()
        self.update_temp_info()
        self.update_process_info()   

    def get_payload(self):
        return {
            "node": self.system_info,
            "time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "cpu": self.cpu_info, 
            "ram": self.ram_info,
            "swap":self.swap_info,
            "disks":self.disk_list,
            "processes": self.process_list,
            "temperatures": self.temp_info
        }           

