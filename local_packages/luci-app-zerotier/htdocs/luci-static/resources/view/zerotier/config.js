/* SPDX-License-Identifier: GPL-3.0-only
 *
 * Copyright (C) 2022 ImmortalWrt.org
 */

'use strict';
'require form';
'require poll';
'require rpc';
'require uci';
'require view';
'require tools.widgets as widgets';

const callServiceList = rpc.declare({
	object: 'service',
	method: 'list',
	params: ['name'],
	expect: { '': {} }
});

function getServiceStatus() {
	return L.resolveDefault(callServiceList('zerotier'), {}).then(function(res) {
		let isRunning = false;
		try {
			isRunning = res['zerotier']['instances']['instance1']['running'];
		} catch (e) { }
		return isRunning;
	});
}

function renderStatus(isRunning) {
	let spanTemp = '<em><span style="color:%s"><strong>%s %s</strong></span></em>';
	let renderHTML;
	if (isRunning)
		renderHTML = String.format(spanTemp, 'green', _('ZeroTier'), _('RUNNING'));
	else
		renderHTML = String.format(spanTemp, 'red', _('ZeroTier'), _('NOT RUNNING'));

	return renderHTML;
}

return view.extend({
	load: function() {
		return uci.load('firewall');
	},
	render: function() {
		let m, s, o;

		m = new form.Map('zerotier', _('ZeroTier'),
			_('ZeroTier is an open source, cross-platform and easy to use virtual LAN.'));
		m.chain('firewall');

		s = m.section(form.TypedSection);
		s.anonymous = true;
		s.render = function() {
			poll.add(function() {
				return L.resolveDefault(getServiceStatus()).then(function(res) {
					let view = document.getElementById('service_status');
					view.innerHTML = renderStatus(res);
				});
			});

			return E('div', { class: 'cbi-section', id: 'status_bar' }, [
				E('p', { id: 'service_status' }, _('Collecting data…'))
			]);
		}

		s = m.section(form.NamedSection, 'global', 'zerotier', _('Global configuration'));

		o = s.option(form.Flag, 'enabled', _('Enable'));

		o = s.option(form.Flag, '_lan_forward', '允许局域网访问 ZeroTier',
			'启用 LAN 到 ZeroTier 的转发及 IPv4 地址伪装。自动使用实际接口地址和路由，无需填写 IP 或网关；不开放 ZeroTier 主动访问 LAN。保存并应用后生效。');
		o.rmempty = false;
		o.cfgvalue = function() {
			return uci.get('firewall', 'lan_to_zt', 'enabled') !== '0' &&
				uci.get('firewall', 'lan_to_zt', 'src') === 'lan' &&
				uci.get('firewall', 'lan_to_zt', 'dest') === 'zerotier' ? '1' : '0';
		};
		o.write = function(section_id, value) {
			if (!uci.get('firewall', 'zt_lan_access'))
				uci.add('firewall', 'zone', 'zt_lan_access');
			Object.entries({ name: 'zerotier', device: 'zt+', input: 'ACCEPT',
				output: 'ACCEPT', forward: 'REJECT', masq: '1', mtu_fix: '1' }).forEach(function(entry) {
				uci.set('firewall', 'zt_lan_access', entry[0], entry[1]);
			});
			if (!uci.get('firewall', 'lan_to_zt'))
				uci.add('firewall', 'forwarding', 'lan_to_zt');
			uci.set('firewall', 'lan_to_zt', 'src', 'lan');
			uci.set('firewall', 'lan_to_zt', 'dest', 'zerotier');
			uci.set('firewall', 'lan_to_zt', 'enabled', value);
		};

		o = s.option(form.Value, 'port', _('Listen port'));
		o.datatype = 'port';

		o = s.option(form.Value, 'secret', _('Client secret'));
		o.password = true;

		o = s.option(form.Value, 'local_conf_path', _('Local config path'),
			_('Path of the optional file local.conf (see <a target="_blank" href="%s">documentation</a>).').format(
				'https://docs.zerotier.com/config/#local-configuration-options'));
		o.value('/etc/zerotier.conf');

		o = s.option(form.Value, 'config_path', _('Config path'),
				_('Persistent configuration directory (to keep other configurations such as controller or moons, etc.).'));
		o.value('/etc/zerotier');

		o = s.option(form.Flag, 'copy_config_path', _('Copy config path'),
				_('Copy the contents of the persistent configuration directory to memory instead of linking it, this avoids writing to flash.'));
		o.depends({'config_path': '', '!reverse': true});

		o = s.option(form.Flag, 'fw_allow_input', _('Allow input traffic'),
			_('Allow input traffic to the ZeroTier daemon.'));

		o = s.option(form.Button, '_panel', _('ZeroTier Central'),
			_('Create or manage your ZeroTier network, and auth clients who could access.'));
		o.inputtitle = _('Open website');
		o.inputstyle = 'apply';
		o.onclick = function() {
			window.open("https://my.zerotier.com/network", '_blank');
		}

		s = m.section(form.GridSection, 'network', _('Network configuration'));
		s.addremove = true;
		s.rowcolors = true;
		s.sortable = true;
		s.nodescriptions = true;

		o = s.option(form.Flag, 'enabled', _('Enable'));
		o.default = o.enabled;
		o.editable = true;

		o = s.option(form.Value, 'id', _('Network ID'));
		o.rmempty = false;
		o.width = '20%';

		o = s.option(form.Flag, 'allow_managed', _('Allow managed IP/route'),
			_('Allow ZeroTier to set IP addresses and routes (local/private ranges only).'));
		o.default = o.enabled;
		o.editable = true;

		o = s.option(form.Flag, 'allow_global', _('Allow global IP/route'),
			_('Allow ZeroTier to set global/public/not-private range IPs and routes.'));
		o.editable = true;

		o = s.option(form.Flag, 'allow_default', _('Allow default route'),
			_('Allow ZeroTier to set the default route on the system.'));
		o.editable = true;

		o = s.option(form.Flag, 'allow_dns', _('Allow DNS'),
			_('Allow ZeroTier to set DNS servers.'));
		o.editable = true;

		o = s.option(form.Flag, 'fw_allow_input', _('Allow input'),
			_('Allow input traffic from the ZeroTier network.'));
		o.editable = true;

		o = s.option(form.Flag, 'fw_allow_forward', _('Allow forward'),
			_('Allow forward traffic from/to the ZeroTier network.'));
		o.editable = true;

		o = s.option(widgets.DeviceSelect, 'fw_forward_ifaces', _('Forward interfaces'),
			_('Leave empty for all.'));
		o.multiple = true;
		o.noaliases = true;
		o.depends('fw_allow_forward', '1');
		o.modalonly = true;

		o = s.option(form.Flag, 'fw_allow_masq', _('Masquerading'),
			_('Enable network address and port translation (NAT) for outbound traffic for this network.'));
		o.editable = true;

		o = s.option(widgets.DeviceSelect, 'fw_masq_ifaces', _('Masquerade interfaces'),
			_('Leave empty for all.'));
		o.multiple = true;
		o.noaliases = true;
		o.depends('fw_allow_masq', '1');
		o.modalonly = true;

		return m.render();
	}
});
