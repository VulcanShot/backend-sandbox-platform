"""Tests for SSH config generation utilities."""

from django.conf import settings

from crczp.sandbox_instance_app.lib import sshconfig


class TestGetSshConfig:
    """Tests for CrczpSSHConfig generation methods."""

    def test_create_user_config_success(self, top_ins, user_ssh_config):
        """Test successful creation of user SSH config from a topology instance."""
        proxy_jump = settings.CRCZP_CONFIG.proxy_jump_to_man
        result = sshconfig.CrczpUserSSHConfig(top_ins, proxy_jump.Host, 'stack-name')
        assert result.asdict() == user_ssh_config.asdict()

    def test_create_management_config_success(self, top_ins, management_ssh_config):
        """Test successful creation of management SSH config."""
        proxy_jump = settings.CRCZP_CONFIG.proxy_jump_to_man
        result = sshconfig.CrczpMgmtSSHConfig(top_ins, proxy_jump.Host, 'pool-prefix')
        assert result.asdict() == management_ssh_config.asdict()

    def test_create_ansible_config_success(self, top_ins, ansible_ssh_config):
        """Test successful creation of ansible SSH config."""
        proxy_jump = settings.CRCZP_CONFIG.proxy_jump_to_man
        result = sshconfig.CrczpAnsibleSSHConfig(
            top_ins,
            '/root/.ssh/pool_mng_key',
            proxy_jump.Host,
            proxy_jump.User,
            '/root/.ssh/id_rsa',
        )
        assert result.asdict() == ansible_ssh_config.asdict()

    def test_password_host_prefers_key_with_password_fallback(self, top_ins):
        """A host with a management password keeps the key and adds a password fallback."""
        server_def = next(h for h in top_ins.topology_definition.hosts if h.name == 'server')
        server_def.base_box.mgmt_password = 'inv3a-t3ch'  # nosec B105

        proxy_jump = settings.CRCZP_CONFIG.proxy_jump_to_man
        result = sshconfig.CrczpMgmtSSHConfig(top_ins, proxy_jump.Host, 'pool-prefix')

        def first_name(host: object) -> str:
            return host[0] if isinstance(host, (list, tuple)) else str(host).split()[0]

        server_entry = next(e for e in result.asdict() if first_name(e['Host']) == 'server')
        assert 'IdentityFile' in server_entry
        assert server_entry.get('IdentitiesOnly')  # truthy (yes)
        assert server_entry.get('PreferredAuthentications') == 'publickey,password'
        assert server_entry.get('PubkeyAuthentication') != 'no'

        # The directives must reach the serialized config that SSH actually reads.
        serialized = result.serialize()
        assert 'PreferredAuthentications publickey,password' in serialized
        assert 'IdentityFile' in serialized

        # A host without a password is untouched (key-based, no password fallback).
        home_entry = next(e for e in result.asdict() if first_name(e['Host']) == 'home')
        assert 'IdentityFile' in home_entry
        assert home_entry.get('IdentitiesOnly')  # truthy (yes)
        assert 'PreferredAuthentications' not in home_entry
