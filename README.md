# tomguo-modules-test：模块兼容性桩仓

放三个不依赖真实站点的假源，供 `native/cmd/probe` 与 CI 校验使用。

```
modules/fake-json/        明文 JSON：catalogPage / search / detail
modules/fake-html/        服务端渲染假页：正则抓取、&amp; 还原
modules/fake-encrypted/   AES-CBC + HMAC + gzip：bodyBase64 链路、pad/unpad
```

每个目录含 `manifest.json` + `main.js`，`allowEmptyCatalog: true`（规范里专为示例/测试模块准备）。

本地跑：

```bash
cd ../tomguo && go build -o /tmp/probe ./native/cmd/probe
mkdir -p /tmp/plugtest/modules
cp -r ../tomguo-modules-test/modules/* /tmp/plugtest/modules/
/tmp/plugtest '{"action":"catalog","source":"fake-json","page":1}'
```

CI 校验（复制进本仓 `.github/workflows/modules-check.yml`）：

```yaml
name: 模块清单校验
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: python3 scripts/fill_module_digest.py modules/ --check
      - run: python3 scripts/check_manifest.py modules/ --strict
```
