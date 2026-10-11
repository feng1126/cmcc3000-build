'use strict';
'require view';
'require form';
'require rpc';
'require poll';
'require fs';
'require ui';

var serviceList = rpc.declare({ object: 'service', method: 'list', params: ['name'], expect: { '': {} } });
return view.extend({
    render: function() {
        var m = new form.Map('npc', 'NPS 客户端', '客户端负责连接云服务器。公网转发端口和目标地址在 NPS 服务端管理，修改下面配置后请保存并应用。');
        var status = E('span', {}, '正在检查…');
        var section = m.section(form.TypedSection);
        section.render = function() {
            poll.add(function() {
                return serviceList('npc-codexweb').then(function(data) {
                    var instances = ((data['npc-codexweb'] || {}).instances || {});
                    var running = Object.keys(instances).some(function(k) { return instances[k].running; });
                    status.textContent = running ? '运行中（连接及转发结果请以实际访问为准）' : '未运行';
                }).catch(function() { status.textContent = '状态读取失败'; });
            });
            return E('div', { class: 'cbi-section' }, [E('h3', {}, '服务状态'), status]);
        };
        var s = m.section(form.NamedSection, 'main', 'npc', '连接配置');
        var o = s.option(form.Flag, 'enabled', '启用客户端');
        o.rmempty = false;
        o = s.option(form.Value, 'server', '服务器地址');
        o.datatype = 'host'; o.rmempty = false;
        o = s.option(form.Value, 'port', '服务器连接端口', '加密隧道连接端口，与网页入口端口不同。');
        o.datatype = 'port'; o.rmempty = false;
        o = s.option(form.Value, 'vkey', '客户端密钥');
        o.password = true; o.rmempty = false;
        o.validate = function(section, value) { return /^[A-Za-z0-9_-]{16,128}$/.test(value) ? true : '密钥需为 16–128 位字母、数字、下划线或连字符'; };
        o = s.option(form.Flag, 'tls', '启用 TLS 加密');
        o.rmempty = false; o.default = '1';
        ['start', 'stop', 'restart'].forEach(function(action, index) {
            var button = s.option(form.Button, '_' + action, ['启动', '停止', '重启'][index]);
            button.inputtitle = ['启动', '停止', '重启'][index];
            button.onclick = function() {
                return fs.exec('/etc/init.d/npc-codexweb', [action]).then(function(result) {
                    if (result.code) throw new Error(result.stderr || result.stdout || '操作失败');
                    ui.addNotification(null, E('p', {}, '操作已执行，状态将在下次刷新时更新。'), 'info');
                }).catch(function(err) { ui.addNotification(null, E('p', {}, err.message), 'error'); });
            };
        });
        return m.render();
    }
});
