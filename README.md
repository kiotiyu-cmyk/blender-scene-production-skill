# Blender Scene Production Skill

从参考图重建、精修 Blender 场景，并交付经过检查的静帧、环绕/内部穿行视频或互动场景。

## 能做什么

- 从轮廓、空间、接触、材质到光照定位差距，保护已确认内容。
- 检查楼梯、平台、池底与相机/角色净空，处理自然溢流、云层和主光关系。
- 为环绕、壁画扫视、道具特写和白模到成品展示设计运镜，先做低成本整段检查再输出高清。
- 区分 Blender 源工程、Cycles/EEVEE 渲染与网页运行结果，跟踪真实完成状态。
- 用工具检查场景依赖、前后画面对照、视频参数和完整解码。

入口：[SKILL.md](SKILL.md)。各专题按需读取，不要求每个任务都执行完整流水线。

## 安装到 Codex

将仓库克隆为技能目录：

```sh
git clone https://github.com/kiotiyu-cmyk/blender-scene-production-skill.git ~/.codex/skills/blender-scene-production
```

如果目标目录已存在，保留本地修改后按你的更新流程同步，不覆盖旧版本。也可将仓库内容放入你的代理支持的技能目录。私有仓库需要该账号的读取权限。

调用示例：

> 使用 $blender-scene-production，检查已有场景的楼梯转角和水景，为它制作横屏环绕及内部穿行素材；先看完整低成本运镜，再渲染高清。

## 工具与依赖

- `scripts/inspect_scene.py`：在 Blender Python 中只读检查场景配置和资源依赖。
- `scripts/compare_review.py`：Pillow 图片对照工具，始终要求视觉审阅。
- `scripts/inspect_video.py`：Python 标准库 + FFprobe；`--decode` 使用 FFmpeg 完整解码，不转码或改动输入。

```sh
python3 scripts/inspect_video.py --input orbit.mp4 --output orbit-check.json --expect-width 3840 --expect-height 2880 --expect-fps 24 --expect-frames 288 --expect-duration 12 --decode
```

尺寸、帧率和可解码性通过，不等于相机没有穿墙或画面已通过视觉验收。

## 来源与范围

本 Skill 结合实际场景制作经验重写，并参考 CORVUS 的 Blender 制作方法，来源与验证范围见 [references/sources.md](references/sources.md)。仓库不包含第三方场景、贴图、模型、配音、项目媒体或凭证；上游资料链接不代表取得其代码与资产再分发许可。

本机路径、4:3 画幅与个案摄影路线不是通用默认。付费生成、最终视觉和发布范围遵从使用者当前授权。
