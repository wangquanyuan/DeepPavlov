import re
from logging import getLogger
from pathlib import Path
from typing import Union

from deeppavlov.core.commands.utils import expand_path
import deeppavlov.models.go_bot.templates as go_bot_templates
from deeppavlov.core.common.registry import register

log = getLogger(__name__)


# todo add the ability to configure nlg loglevel in config (now the setting is shared across all the GO-bot)
# todo add each method input-output logging when proper loglevel level specified

@register("gobot_nlg_manager")
class NLGManager:
    """
    NLGManager is a unit of the go-bot pipeline that handles the generation of text
    when the pattern is chosen among the known patterns and the named-entities-values-like knowledge is provided.
    (the whole go-bot pipeline is as follows: NLU, dialogue-state-tracking&policy-NN, NLG)

    Parameters:
        template_path: file with mapping between actions and text templates
            for response generation.
        template_type: type of used response templates in string format.
        api_call_action: label of the action that corresponds to database api call
            (it must be present in your ``template_path`` file), during interaction
            it will be used to get ``'db_result'`` from ``database``.
        debug: whether to display debug output.
    """

    def __init__(self, template_path: Union[str, Path], template_type: str, api_call_action: str, debug = False):
        self.debug = debug
        if self.debug:
            log.debug(f"BEFORE {self.__class__.__name__} init(): "
                      f"template_path={template_path}, template_type={template_type}, "
                      f"api_call_action={api_call_action}, debug={debug}")

        template_path = expand_path(template_path)
        template_type = getattr(go_bot_templates, template_type)
        self.templates = go_bot_templates.Templates(template_type).load(template_path)

        self.api_call_id = -1
        if api_call_action is not None:
            self.api_call_id = self.templates.actions.index(api_call_action)

        if self.debug:
            log.debug(f"AFTER {self.__class__.__name__} init(): "
                      f"template_path={template_path}, template_type={template_type}, "
                      f"api_call_action={api_call_action}, debug={debug}")

    def get_action_id(self, action_text: str) -> int:
        """
        Looks up for an ID relevant to the passed action text in the list of known actions and their ids.
        :param action_text: the text for which an ID needs to be returned.
        :return: an ID corresponding to the passed action text
        """
        return self.templates.actions.index(action_text)  # todo unhandled exception when not found

    def decode_response(self, action_id: int, tracker_slotfilled_state: dict) -> str:
        """
        Convert action template id and known slot values from tracker to response text.
        Replaces the unknown slot values with "dontcare" if the action is an API call.
        :param action_id: the id of action to generate text for.
        :param tracker_slotfilled_state: the slots and their known values. usually received from dialogue state tracker.

        :returns: the text generated for the passed action id and slot values.
        """
        action_text = self._generate_slotfilled_text_for_action(action_id, tracker_slotfilled_state)
        # in api calls replace unknown slots to "dontcare"
        if action_id == self.api_call_id:
            action_text = re.sub("#([A-Za-z]+)", "dontcare", action_text).lower()
        return action_text

    def _generate_slotfilled_text_for_action(self, action_id: int, slots: dict) -> str:
        """
        Generate text for the predicted speech action using the pattern provided for the action.
        The slotfilled state provides info to encapsulate to the pattern.

        :param action_id: the id of action to generate text for.
        :param slots: the slots and their known values. usually received from dialogue state tracker.

        :returns: the text generated for the passed action id and slot values.
        """
        text = self.templates.templates[action_id].generate_text(slots)
        return text

    def num_of_known_actions(self) -> int:
        """
        :returns: the number of actions known to the NLG module
        """
        return len(self.templates)
