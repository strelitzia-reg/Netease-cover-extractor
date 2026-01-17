"""
网易云专辑封面下载器 - 数据解析
"""

import os
import sys
import re
import time
import requests
import json

class NeteaseCoverDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://music.163.com/',
        })
    
    def extract_id(self, url):
        """从URL提取ID"""
        try:
            url = url.strip()
            
            if re.match(r'^\d+$', url):
                return 'song', url
            
            patterns = [
                (r'song\?id=(\d+)', 'song'),
                (r'/song/(\d+)', 'song'),
                (r'#/song\?id=(\d+)', 'song'),
                (r'album\?id=(\d+)', 'album'),
                (r'/album/(\d+)', 'album'),
                (r'#/album\?id=(\d+)', 'album'),
            ]
            
            for pattern, type_ in patterns:
                match = re.search(pattern, url, re.IGNORECASE)
                if match:
                    return type_, match.group(1)
            
            return None, None
        except Exception:
            return None, None
    
    def debug_api_response(self, music_id, music_type):
        """调试API响应，查看原始数据结构"""
        print("\n🔍 调试API响应...")
        try:
            if music_type == 'song':
                url = f'https://music.163.com/api/song/detail?ids=[{music_id}]'
            else:
                url = f'https://music.163.com/api/album/{music_id}'
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"API返回数据 (前500字符):")
                print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
                
                if music_type == 'song' and data.get('songs'):
                    song = data['songs'][0]
                    print(f"\n歌曲数据结构分析:")
                    print(f"所有键: {list(song.keys())}")
                    
                    # 查找可能的艺人字段
                    for key in song.keys():
                        if 'artist' in key.lower() or 'ar' == key:
                            print(f"艺人相关字段 '{key}': {song[key]}")
                    
                    # 查找可能的专辑字段
                    for key in song.keys():
                        if 'album' in key.lower() or 'al' == key:
                            print(f"专辑相关字段 '{key}': {song[key]}")
                    
                    # 查找可能的封面字段
                    for key in song.keys():
                        if 'pic' in key.lower() or 'cover' in key.lower():
                            print(f"封面相关字段 '{key}': {song[key]}")
                
                return True
        except Exception as e:
            print(f"调试失败: {e}")
        
        return False
    
    def extract_song_info_enhanced(self, song_data):
        """歌曲信息提取"""
        info = {
            'name': '未知歌曲',
            'artist': '未知艺人',
            'album': '未知专辑',
            'cover_url': '',
            'album_id': '',
            'type': 'song'
        }
        
        try:
            # 提取歌曲名
            if 'name' in song_data:
                info['name'] = song_data['name']
            
            # 提取艺人信息 - 尝试多种字段
            artists = []
            
            # 尝试字段 'ar' (最常见)
            if 'ar' in song_data and isinstance(song_data['ar'], list):
                for artist in song_data['ar']:
                    if isinstance(artist, dict) and 'name' in artist:
                        artists.append(artist['name'])
            
            # 尝试字段 'artists' (备选)
            elif 'artists' in song_data and isinstance(song_data['artists'], list):
                for artist in song_data['artists']:
                    if isinstance(artist, dict) and 'name' in artist:
                        artists.append(artist['name'])
            
            # 尝试字段 'artist' (单数形式)
            elif 'artist' in song_data:
                if isinstance(song_data['artist'], dict) and 'name' in song_data['artist']:
                    artists.append(song_data['artist']['name'])
                elif isinstance(song_data['artist'], str):
                    artists.append(song_data['artist'])
            
            if artists:
                info['artist'] = artists[0] if len(artists) == 1 else ', '.join(artists)
            
            # 提取专辑信息 - 尝试多种字段
            album_data = None
            
            # 尝试字段 'al' (最常见)
            if 'al' in song_data and isinstance(song_data['al'], dict):
                album_data = song_data['al']
            # 尝试字段 'album' (备选)
            elif 'album' in song_data and isinstance(song_data['album'], dict):
                album_data = song_data['album']
            
            if album_data:
                info['album'] = album_data.get('name', '未知专辑')
                info['album_id'] = str(album_data.get('id', ''))
                
                # 提取封面URL - 尝试多种字段
                if 'picUrl' in album_data:
                    info['cover_url'] = album_data['picUrl']
                elif 'pic_url' in album_data:
                    info['cover_url'] = album_data['pic_url']
                elif 'pic' in album_data and album_data['pic']:
                    pic_id = str(album_data['pic'])
                    info['cover_url'] = f"https://p1.music.126.net/{pic_id}/{pic_id}.jpg"
            
            # 如果还没有封面URL，尝试从歌曲本身获取
            if not info['cover_url']:
                if 'picUrl' in song_data:
                    info['cover_url'] = song_data['picUrl']
                elif 'pic' in song_data and song_data['pic']:
                    pic_id = str(song_data['pic'])
                    info['cover_url'] = f"https://p1.music.126.net/{pic_id}/{pic_id}.jpg"
            
            return info
            
        except Exception as e:
            print(f"提取歌曲信息出错: {e}")
            return info
    
    def extract_album_info_enhanced(self, album_data):
        """增强版的专辑信息提取"""
        info = {
            'name': '未知专辑',
            'artist': '未知艺人',
            'album': '未知专辑',
            'cover_url': '',
            'album_id': '',
            'type': 'album'
        }
        
        try:
            # 提取专辑名
            if 'name' in album_data:
                info['name'] = info['album'] = album_data['name']
            
            # 提取专辑ID
            if 'id' in album_data:
                info['album_id'] = str(album_data['id'])
            
            # 提取艺人信息
            if 'artist' in album_data:
                if isinstance(album_data['artist'], dict):
                    info['artist'] = album_data['artist'].get('name', '未知艺人')
                elif isinstance(album_data['artist'], str):
                    info['artist'] = album_data['artist']
            
            # 提取封面URL
            if 'picUrl' in album_data:
                info['cover_url'] = album_data['picUrl']
            elif 'pic' in album_data and album_data['pic']:
                pic_id = str(album_data['pic'])
                info['cover_url'] = f"https://p1.music.126.net/{pic_id}/{pic_id}.jpg"
            elif 'blurPicUrl' in album_data:
                info['cover_url'] = album_data['blurPicUrl']  # 模糊封面作为备选
            
            return info
            
        except Exception as e:
            print(f"提取专辑信息出错: {e}")
            return info
    
    def get_music_info(self, music_id, music_type):
        """获取音乐信息"""
        try:
            if music_type == 'song':
                url = f'https://music.163.com/api/song/detail?ids=[{music_id}]'
            else:
                url = f'https://music.163.com/api/album/{music_id}'
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if music_type == 'song':
                    if data.get('songs') and data['songs']:
                        song = data['songs'][0]
                        return self.extract_song_info_enhanced(song)
                else:  # album
                    if data.get('album'):
                        album = data['album']
                        return self.extract_album_info_enhanced(album)
        
        except Exception as e:
            print(f"获取信息失败: {e}")
        
        return None
    
    def get_hd_cover_url(self, base_url):
        """获取高清封面URL"""
        if not base_url:
            return None
        
        # 尝试几种高清参数
        urls_to_try = []
        
        # 移除已有参数
        if '?' in base_url:
            clean_url = base_url.split('?')[0]
        else:
            clean_url = base_url
        
        # 超大尺寸
        for size in ['9999y9999', '2000y2000', '1500y1500', '1080y1080']:
            urls_to_try.append(f"{clean_url}?param={size}")
        
        # WebP格式
        if clean_url.endswith('.jpg'):
            webp_url = clean_url.replace('.jpg', '.webp')
            urls_to_try.append(webp_url)
            urls_to_try.append(f"{webp_url}?param=9999y9999")
        
        # 原始URL
        urls_to_try.append(base_url)
        
        # 测试每个URL
        best_url = base_url
        best_size = 0
        
        for url in urls_to_try:
            try:
                response = self.session.head(url, timeout=3)
                if response.status_code == 200:
                    size = int(response.headers.get('content-length', 0))
                    if size > best_size:
                        best_size = size
                        best_url = url
            except:
                continue
        
        return best_url
    
    def download_cover(self, url, save_path):
        """下载封面"""
        try:
            response = self.session.get(url, timeout=15, stream=True)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # 验证文件
                if os.path.exists(save_path):
                    file_size = os.path.getsize(save_path)
                    return file_size if file_size > 0 else 0
        except Exception as e:
            print(f"下载失败: {e}")
        
        return 0
    
    def sanitize_name(self, name):
        """清理名称中的非法字符"""
        if not name:
            return "unknown"
        
        # 移除非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        name = re.sub(illegal_chars, '_', name)
        
        # 限制长度
        if len(name) > 50:
            name = name[:50]
        
        return name.strip()
    
    def process_url(self, url):
        """处理URL的主函数"""
        print("\n" + "=" * 60)
        print("开始处理...")
        print("=" * 60)
        
        # 提取ID
        music_type, music_id = self.extract_id(url)
        if not music_id:
            print("❌ 无法识别链接格式")
            print("\n请使用以下格式之一:")
            print("  • https://music.163.com/#/song?id=123456")
            print("  • https://music.163.com/song?id=123456")
            print("  • 直接输入数字ID: 123456")
            return False
        
        print(f"✓ 解析成功: {music_type.upper()} ID={music_id}")
        
        # 获取信息
        info = self.get_music_info(music_id, music_type)
        if not info:
            print("❌ 无法获取音乐信息")
            print("可能原因: 歌曲不存在、网络问题或API限制")
            
            # 调试模式
            debug_choice = input("是否查看API原始数据? (y/n): ").strip().lower()
            if debug_choice == 'y':
                self.debug_api_response(music_id, music_type)
            
            return False
        
        print(f"✓ 名称: {info['name']}")
        print(f"✓ 艺人: {info['artist']}")
        print(f"✓ 专辑: {info['album']}")
        
        if not info['cover_url']:
            print("❌ 该歌曲/专辑没有封面")
            
            # 调试模式
            debug_choice = input("是否查看API原始数据? (y/n): ").strip().lower()
            if debug_choice == 'y':
                self.debug_api_response(music_id, music_type)
            
            return False
        
        # 获取高清URL
        hd_url = self.get_hd_cover_url(info['cover_url'])
        print(f"✓ 封面URL: {hd_url[:80]}..." if len(hd_url) > 80 else f"✓ 封面URL: {hd_url}")
        
        # 创建保存目录
        save_dir = "网易云专辑封面"
        try:
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
        except Exception as e:
            print(f"❌ 无法创建目录: {e}")
            return False
        
        # 创建艺人-专辑子目录
        artist_dir = self.sanitize_name(info['artist'])
        album_dir = self.sanitize_name(info['album'])
        
        if artist_dir and album_dir and artist_dir != album_dir:
            sub_dir = os.path.join(save_dir, f"{artist_dir} - {album_dir}")
        elif album_dir:
            sub_dir = os.path.join(save_dir, album_dir)
        else:
            album_id = info.get('album_id', str(int(time.time())))
            sub_dir = os.path.join(save_dir, f"album_{album_id}")
        
        try:
            if not os.path.exists(sub_dir):
                os.makedirs(sub_dir)
        except Exception as e:
            print(f"❌ 无法创建子目录: {e}")
            sub_dir = save_dir  # 使用主目录
        
        print(f"✓ 保存到: {sub_dir}")
        
        # 生成文件名
        # 确定文件扩展名
        if '.webp' in hd_url.lower():
            file_ext = 'webp'
        else:
            file_ext = 'jpg'
        
        # 文件名：优先使用专辑名，其次使用歌曲名
        if info['album'] != '未知专辑':
            base_name = info['album']
        else:
            base_name = info['name']
        
        safe_name = self.sanitize_name(base_name)
        filename = f"{safe_name}.{file_ext}"
        save_path = os.path.join(sub_dir, filename)
        
        # 避免覆盖
        counter = 1
        while os.path.exists(save_path):
            filename = f"{safe_name}_{counter}.{file_ext}"
            save_path = os.path.join(sub_dir, filename)
            counter += 1
        
        print(f"✓ 文件名: {filename}")
        print("-" * 60)
        
        # 下载封面
        print("正在下载封面...")
        file_size = self.download_cover(hd_url, save_path)
        
        if file_size > 0:
            size_kb = file_size / 1024
            
            print(f"\n🎉 下载成功!")
            print(f"📁 文件: {filename}")
            print(f"💾 大小: {size_kb:.1f} KB")
            print(f"📂 位置: {os.path.abspath(save_path)}")
            
            # 显示文件验证信息
            if os.path.exists(save_path):
                actual_size = os.path.getsize(save_path)
                print(f"✅ 文件验证: 存在 ({actual_size} 字节)")
            else:
                print("❌ 文件验证: 不存在!")
                return False
            
            # 质量评级
            if size_kb > 200:
                print("✨ 质量: 极佳")
            elif size_kb > 100:
                print("⭐ 质量: 良好")
            elif size_kb > 50:
                print("👍 质量: 普通")
            else:
                print("📱 质量: 较低")
            
            print("=" * 60)
            return True
        else:
            print("❌ 下载失败")
            return False

def main():
    """主程序"""
    print("=" * 60)
    print("网易云专辑封面下载器 - 增强版")
    print("=" * 60)
    
    # 环境检查
    print("检查环境中...")
    
    # 检查Python版本
    if sys.version_info.major < 3 or (sys.version_info.major == 3 and sys.version_info.minor < 6):
        print("❌ Python版本过低，请安装 Python 3.6 或更高版本")
        input("\n按 Enter 键退出...")
        return
    
    print(f"✓ Python版本: {sys.version}")
    
    # 检查requests库
    try:
        import requests
        print(f"✓ requests库已安装: {requests.__version__}")
    except ImportError:
        print("❌ requests库未安装")
        print("\n请运行: pip install requests")
        input("\n按 Enter 键退出...")
        return
    
    print("\n" + "=" * 60)
    print("特点:")
    print("  • 增强数据解析")
    print("  • 自动创建艺人-专辑文件夹")
    print("  • 智能获取高清封面")
    print("  • 支持调试模式，可查看API原始数据")
    print("=" * 60)
    
    downloader = NeteaseCoverDownloader()
    
    while True:
        try:
            print("\n请输入网易云链接 (输入 'q' 退出):")
            print("示例: https://music.163.com/#/song?id=1901371647")
            user_input = input(">> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['q', 'quit', 'exit', '退出']:
                print("\n感谢使用，再见！")
                break
            
            # 处理链接
            success = downloader.process_url(user_input)
            
            if success:
                print(f"✓ 操作完成")
            else:
                print(f"✗ 操作失败，请检查链接或重试")
            
            # 询问是否继续
            print("\n是否继续下载? (输入 'y' 继续，其他键退出): ", end='')
            choice = input().strip().lower()
            
            if choice not in ['y', 'yes', '是', '继续', '']:
                print("\n感谢使用，再见！")
                break
            
            print("\n" + "=" * 60)
            
        except KeyboardInterrupt:
            print("\n\n操作被中断")
            break
        except Exception as e:
            print(f"\n发生错误: {e}")
            print("请重试...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        print("\n请尝试以下解决方法:")
        print("1. 确保已安装 Python 3.6+")
        print("2. 运行命令: pip install requests")
        print("3. 检查网络连接")
    
    # 等待用户确认退出
    input("\n按 Enter 键退出程序...")