
import os
import sys
import yaml
import shutil
import tempfile
import subprocess

from . import helpers


class Builder(object):
    def __init__(self, name, template, subordinate=False, hook='hooks.py'):
        self.metadata = {'name': name,
                         'summary': 'Generated by Amulet',
                         'description': 'Generated by Amulet',
                         'subordinate': subordinate,
                         'maintainer': 'Amulet Built <juju@lists.ubuntu.com>'}

        self.hook = hook

        self.template = os.path.realpath(template)
        if not os.path.exists(self.template):
            raise IOError('%s does not exist' % self.template)

        d = tempfile.mkdtemp(prefix='sentry%s_'
                             % ('-sub' if subordinate else ''))
        self.charm = os.path.join(d, name)
        shutil.copytree(self.template, self.charm, symlinks=True)

        with open(os.devnull, 'w') as devnull:
            try:
                subprocess.check_call(['bzr', 'init'], cwd=self.charm,
                                      stdout=devnull, stderr=devnull)
            except subprocess.CalledProcessError:
                raise IOError('Unable to create bzr repo')

        if subordinate:
            self.require('juju-info', 'juju-info', {'scope': 'container'})

        os.chmod(os.path.join(self.charm, 'hooks', self.hook), 0o755)

    def require(self, relation, interface, opts={}):
        self._add_relation(relation, interface, 'requires', opts)

    def provide(self, relation, interface, opts={}):
        self._add_relation(relation, interface, 'provides', opts)

    def peer(self, relation, interface, opts={}):
        self._add_relation(relation, interface, 'peers', opts)

    def _add_relation(self, relation, interface, name, opts={}):
        if not name in self.metadata:
            self.metadata[name] = {}

        self.metadata[name][relation] = opts
        self.metadata[name][relation]['interface'] = interface

        # Build symlink to "global hooks" file
        if self.hook:
            for event in ['joined', 'changed', 'departed', 'broken']:
                hook_file = os.path.join(self.charm, 'hooks', '%s-relation-%s'
                                         % (relation, event))
                if not os.path.exists(hook_file):
                    os.symlink(self.hook, hook_file)

        self.write_metadata()

    def write_metadata(self):
        metadata = yaml.dump(self.metadata, default_flow_style=False)
        with open(os.path.join(self.charm, 'metadata.yaml'), 'w') as m:
            m.write(metadata)

        self.save()

    def save(self):
        with open(os.devnull, 'w') as devnull:
            try:
                subprocess.check_call(['bzr', 'add', '.'], cwd=self.charm,
                                      stdout=devnull, stderr=devnull)
                subprocess.check_call(['bzr', 'commit', '-m', 'Checkpoint'],
                                      cwd=self.charm, stdout=devnull,
                                      stderr=devnull)
            except subprocess.CalledProcessError:
                raise IOError('Unable to update bzr repo')
