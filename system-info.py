import os
import platform
import subprocess
import psutil
import json
from datetime import datetime
import socket

class SystemInfo:
    def __init__(self):
        self.info = {}
    
    def get_system_overview(self):
        return {
            "hostname": socket.gethostname(),
            "os": f"{platform.system()} {platform.release()}",
            "kernel": platform.version(),
            "architecture": platform.machine(),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "uptime": self._get_uptime()
        }
    
    def get_cpu_info(self):
        try:
            result = subprocess.run(['lscpu'], capture_output=True, text=True)
            cpu_info = {}
            
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    cpu_info[key.strip()] = value.strip()
            
            cpu_info['current_load_percent'] = psutil.cpu_percent(interval=1)
            cpu_info['cpu_cores_physical'] = psutil.cpu_count(logical=False)
            cpu_info['cpu_cores_logical'] = psutil.cpu_count(logical=True)
            return cpu_info
        
        except Exception as e:
            return {"error": str(e)}
    
    def get_memory_info(self):
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percentage_used": memory.percent,
                "swap_total_gb": round(swap.total / (1024**3), 2),
                "swap_used_gb": round(swap.used / (1024**3), 2),
                "swap_percentage": swap.percent
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_storage_info(self):
        storage_info = []
        
        try:
            result = subprocess.run(
                ['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT,MODEL', '-d', '-n'], 
                capture_output=True, 
                text=True
            )
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split()
                    if len(parts) >= 3 and parts[2] == 'disk':
                        disk_name = parts[0]
                        disk_size = parts[1]
                        disk_model = ' '.join(parts[4:]) if len(parts) > 4 else 'Unknown'
                        
                        storage_info.append({
                            "device": disk_name,
                            "size": disk_size,
                            "model": disk_model
                        })
            
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    storage_info.append({
                        "partition": partition.device,
                        "mountpoint": partition.mountpoint,
                        "filesystem": partition.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "percentage_used": usage.percent
                    })
                except PermissionError:
                    continue
                    
            return storage_info
        except Exception as e:
            return {"error": str(e)}
    
    def get_gpu_info(self):
        gpu_info = []
        
        try:
            result = subprocess.run(
                ['lspci', '-v', '-nn'],
                capture_output=True,
                text=True
            )
            lines = result.stdout.split('\n')
            i = 0

            while i < len(lines):
                if 'VGA' in lines[i] or '3D' in lines[i] or 'Display' in lines[i]:
                    gpu = {"details": lines[i].strip()}
                    
                    for j in range(i+1, min(i+10, len(lines))):
                        if 'Subsystem' in lines[j] or 'Memory' in lines[j]:
                            gpu['additional_info'] = lines[j].strip()
                        elif not lines[j].startswith('\t') and lines[j].strip():
                            break
                    
                    gpu_info.append(gpu)
                i += 1

            try:
                glx_result = subprocess.run(
                    ['glxinfo', '-B'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                opengl_info = {}
                for line in glx_result.stdout.split('\n'):
                    if ':' in line and ('OpenGL' in line or 'Device' in line):
                        key, value = line.split(':', 1)
                        opengl_info[key.strip()] = value.strip()
                
                if opengl_info:
                    gpu_info.append({"opengl_info": opengl_info})
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            return gpu_info if gpu_info else {"message": "GPU информация не найдена"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_processes_info(self, limit=20):
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 
                                           'memory_percent', 'status', 'create_time']):
                try:
                    proc_info = proc.info
                    proc_info['memory_mb'] = round(
                        proc.memory_info().rss / (1024 * 1024), 2
                    )
                    processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            return processes[:limit]
        except Exception as e:
            return {"error": str(e)}
    
    def _get_uptime(self):
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
            
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            return f"{days}д {hours}ч {minutes}м"
        except:
            return "Неизвестно"
    
    def get_network_info(self):
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            
            network_info = {
                "hostname": hostname,
                "ip_address": ip_address,
                "interfaces": []
            }
            
            for interface, addresses in psutil.net_if_addrs().items():
                for addr in addresses:
                    if addr.family == socket.AF_INET:
                        network_info["interfaces"].append({
                            "interface": interface,
                            "ip": addr.address,
                            "netmask": addr.netmask
                        })
            
            return network_info
        
        except Exception as e:
            return {"error": str(e)}
    
    def get_all_info(self, processes_limit=20):
        all_info = {
            "system_overview": self.get_system_overview(),
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info(),
            "storage": self.get_storage_info(),
            "gpu": self.get_gpu_info(),
            "network": self.get_network_info(),
            "top_processes": self.get_processes_info(processes_limit)
        }
        
        return all_info
    
    def display_info(self, processes_limit=20):
        info = self.get_all_info(processes_limit)
        
        overview = info['system_overview']
        print(f"\nINFO")
        print(f"  host: {overview.get('hostname', 'N/A')}")
        print(f"  OS: {overview.get('os', 'N/A')}")
        print(f"  kernel: {overview.get('kernel', 'N/A')}")
        print(f"  architecture: {overview.get('architecture', 'N/A')}")
        print(f"  uptime: {overview.get('uptime', 'N/A')}")
        
        # CPU
        cpu = info['cpu']
        if 'error' not in cpu:
            print(f"\nCPU:")
            print(f"  Model: {cpu.get('Model name', 'N/A')}")
            print(f"  cpu_cores_physical: {cpu.get('cpu_cores_physical', 'N/A')}")
            print(f"  cpu_cores_logical: {cpu.get('cpu_cores_logical', 'N/A')}")
            print(f"  load: {cpu.get('current_load_percent', 'N/A')}%")
        
        # Memory
        memory = info['memory']
        if 'error' not in memory:
            print(f"\nMEMORY:")
            print(f"  total RAM: {memory.get('total_gb', 'N/A')} GB")
            print(f"  used RAM: {memory.get('used_gb', 'N/A')} GB ({memory.get('percentage_used', 'N/A')}%)")
            print(f"  available RAM: {memory.get('available_gb', 'N/A')} GB")
            if memory.get('swap_total_gb', 0) > 0:
                print(f"  Swap: {memory.get('swap_used_gb', 0)} GB / {memory.get('swap_total_gb', 0)} GB")
        
        # Storage
        storage = info['storage']
        if storage and 'error' not in storage:
            print(f"\nSTORAGE:")
            for device in storage:
                if 'model' in device:
                    print(f"  Disk: {device['device']} ({device['model']}) - {device['size']}")
                elif 'partition' in device:
                    print(f"  Раздел: {device['partition']} ({device['mountpoint']}) - "
                          f"{device['used_gb']}/{device['total_gb']} GB ({device['percentage_used']}%)")
        
        # GPU
        gpu = info['gpu']
        if gpu and 'error' not in gpu:
            print(f"\nGRAPHICS:")
            for device in gpu:
                if 'details' in device:
                    print(f"  {device['details']}")
                if 'opengl_info' in device:
                    print(f"  OpenGL: {device['opengl_info']}")
        
        # Сеть
        network = info['network']
        if 'error' not in network:
            print(f"\nNETWORK:")
            print(f"  IP addr: {network.get('ip_address', 'N/A')}")
            for iface in network.get('interfaces', []):
                print(f"  Interface: {iface['interface']} - {iface['ip']}")
        
        # Процессы
        processes = info['top_processes']
        if processes and 'error' not in processes:
            print(f"\nProcess:")
            print(f"  {'PID':<8} {'Name':<20} {'CPU%':<8} {'RAM (MB)':<10} {'Статус':<10}")
            print("  " + "-" * 56)
            for proc in processes[:processes_limit]:
                print(f"  {proc['pid']:<8} {proc['name'][:20]:<20} "
                      f"{proc.get('cpu_percent', 0):<8.1f} {proc.get('memory_mb', 0):<10.1f} "
                      f"{proc.get('status', 'N/A'):<10}")
        
        print("\n" + "=" * 60)
        
        return info
    
    def save_to_json(self, filename='system_info.json', processes_limit=20):
        # Сохранение в JSON формат

        info = self.get_all_info(processes_limit)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
        
        print(f"Save: {filename}")
        return filename

def main():
    try:
        import psutil
    except ImportError:
        print("install psutil:")
        exit(1)

    system = SystemInfo()
    system.display_info(processes_limit=15)
    
    # Сохранение в JSON
    save = input("\Save in JSON format? (y/n): ").lower()
    if save == 'y':
        filename = input("Имя файла (default: system_info.json): ").strip()
        if not filename:
            filename = 'system_info.json'
        system.save_to_json(filename)

if __name__ == "__main__":
    main()