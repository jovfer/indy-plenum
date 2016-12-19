import pip
import importlib
from typing import Dict
import time

from plenum.common.log import getlogger

logger = getlogger()


notifierPluginTriggerEvents = {
    'nodeRequestSpike': 'NodeRequestSuspiciousSpike',
    'clusterThroughputSpike': 'ClusterThroughputSuspiciousSpike',
    # TODO: Implement clusterLatencyTooHigh event triggering
    'clusterLatencyTooHigh': 'ClusterLatencyTooHigh'
}


class PluginManager:
    prefix = 'sovrinnotifier'
    __instance = None

    def __new__(cls):
        if PluginManager.__instance is None:
            PluginManager.__instance = object.__new__(cls)
        return PluginManager.__instance

    def __init__(self):
        self.plugins = []
        self.importPlugins()

    def sendMessageUponSuspiciousSpike(self, event: str, historicalData: Dict,
                                       newVal: float, minCnt: int):
        val = historicalData['value']
        cnt = historicalData['cnt']
        historicalData['value'] = \
            val * (cnt / (cnt + 1)) + newVal / (cnt + 1)
        historicalData['cnt'] += 1

        if historicalData[
            'cnt'] < minCnt:
            logger.debug('Not enough data to detect a {} spike'.format(event))
            return

        return self._sendMessage(
            event,
            '{} suspicious spike has been noticed at {}. Usual thoughput: {}. New throughput: {}.'
                .format(event, time.time(), val, newVal)
        )

    def importPlugins(self):
        plugins = self._findPlugins()
        i = 0
        for plugin in plugins:
            try:
                module = importlib.import_module(plugin)
                self.plugins.append(module)
                i += 1
            except Exception as e:
                logger.error('Importing module {} failed due to {}'
                             .format(plugin, e))
        return i, len(plugins)

    def _sendMessage(self, topic, message):
        i = 0
        for plugin in self.plugins:
            try:
                plugin.send_message(topic, message)
                i += 1
            except Exception as e:
                logger.error('Sending message failed for plugin {} due to {}'
                             .format(plugin.__name__, e))
        return i, len(self.plugins)

    def _findPlugins(self):
        return [pkg.key
                for pkg in pip.utils.get_installed_distributions()
                if pkg.key.startswith(PluginManager.prefix)]