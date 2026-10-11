/* This is free software, licensed under the Apache License, Version 2.0
 *
 * Copyright (C) 2024 Sergey Ponomarev <stokito@gmail.com>
 */

'use strict';
'require view';
'require fs';
'require rpc';

var callServiceList = rpc.declare({ object: 'service', method: 'list', params: ['name'], expect: { '': {} } });

function listTunnels() {
	let command = '/usr/bin/cloudflared';
	let commandArgs = ['tunnel', 'list', '-o', 'json'];
	return fs.exec(command, commandArgs).then(function (res) {
		if (res.code === 0) {
			var tunnels = JSON.parse(res.stdout);
			if (!Array.isArray(tunnels)) throw new Error('Invalid tunnel list response');
			return tunnels.map(function (tunnel) {
				tunnel.connections = Array.isArray(tunnel.connections) ? tunnel.connections : [];
				return tunnel;
			});
		} else {
			throw new Error(res.stdout + ' ' + res.stderr);
		}
	});
}

return view.extend({
	handleSaveApply: null,
	handleSave: null,
	handleReset: null,

	load: function () {
		return Promise.all([
			listTunnels().then(function (tunnels) { return { tunnels: tunnels }; })
				.catch(function (error) { return { tunnels: [], error: error.message }; }),
			callServiceList('cloudflared').catch(function () { return {}; })
		]);
	},

	render: function (data) {
		var result = data[0];
        var tunnels = result.tunnels;
        if (result.error) {
            var instances = ((data[1] || {}).cloudflared || {}).instances || {};
            var running = Object.keys(instances).some(function (name) { return instances[name].running === true; });
            return E('div', { 'class': 'cbi-section' }, [
                E('h2', {}, _('Tunnels')),
                E('p', {}, '本机 Cloudflare Tunnel 服务：' + (running ? '运行中' : '未运行或状态不可读取')),
                E('p', {}, '无法读取 Cloudflare 云端隧道列表。云端列表授权与运行隧道的凭据不同，此错误不能用于判断隧道是否断开。'),
                E('pre', {}, result.error),
                E('p', {}, /unauthorized/i.test(result.error) ? '现有账户证书无法查询列表。请重新授权具有隧道查看权限的账户证书；已配置的隧道凭据保持不变。' : '请检查设备 DNS、网络连接及账户证书。'),
                E('a', { href: L.url('admin/vpn/cloudflared/log') }, '查看本机隧道日志')
            ]);
        }

		var tunnelRows = tunnels.map(function (tunnel, index) {
			var rowClass = index % 2 === 0 ? 'cbi-rowstyle-1' : 'cbi-rowstyle-2';
			var tunneldate = new Date(tunnel.created_at).toLocaleString();
			return E('tr', { 'class': 'tr ' + rowClass }, [
				E('td', {'class': 'td'}, tunnel.name),
				E('td', {'class': 'td'}, tunnel.id),
				E('td', {'class': 'td'}, tunneldate),
				E('td', {'class': 'td'}, tunnel.connections.length)
			]);
		});

		var tunnelTable = [
			E('h3', _('Tunnels Information')),
			E('table', { 'class': 'table cbi-section-table' }, [
				E('tr', { 'class': 'tr table-titles' }, [
					E('th', {'class': 'th'}, _('Name')),
					E('th', {'class': 'th'}, _('ID')),
					E('th', {'class': 'th'}, _('Created At')),
					E('th', {'class': 'th'}, _('Connections'))
				]),
				E(tunnelRows)
			])
		];

		var connectionsTables = tunnels.map(function (tunnel) {
			var connectionsTable;
			if (tunnel.connections.length > 0) {
				var connectionRows = tunnel.connections.map(function (connection, index) {
					var rowClass = index % 2 === 0 ? 'cbi-rowstyle-1' : 'cbi-rowstyle-2';
					var connectiondate = new Date(connection.opened_at).toLocaleString();
					return E('tr', { 'class': 'tr ' + rowClass }, [
						E('td', {'class': 'td'}, connection.id),
						E('td', {'class': 'td'}, connection.origin_ip),
						E('td', {'class': 'td'}, connectiondate),
						E('td', {'class': 'td'}, connection.colo_name)
					]);
				});

				connectionsTable = E('table', { 'class': 'table cbi-section-table' }, [
					E('tr', { 'class': 'tr table-titles' }, [
						E('th', {'class': 'th'}, _('Connection ID')),
						E('th', {'class': 'th'}, _('Origin IP')),
						E('th', {'class': 'th'}, _('Opened At')),
						E('th', {'class': 'th'}, _('Data Center'))
					]),
					E(connectionRows)
				]);
			} else {
				connectionsTable = E('div', {'class':'cbi-value center'}, [
					E('em', _('No connections'))
				]);
			}

			return E('div', {'class': 'cbi-section'}, [
				E('h3', _('Connections') + ' ' + tunnel.name),
				E(connectionsTable)
			]);
		});

		return E([], [
			E('h2', { 'class': 'section-title' }, _('Tunnels')),
			E('div', {'class': 'cbi-section'}, tunnelTable),
			E(connectionsTables)
		]);
	}
});
