"""Fail-closed text/function-call subset of native model APIs."""
from .contracts import InspectionError


def validate_llm(value, route, *, response=False):
  if not isinstance(value,dict):raise InspectionError('unsupported_llm_envelope')
  if not response and route.rule.resource_pointer:
    if value.get('model') not in route.allowed_models:raise InspectionError('model_not_allowed')
  # Encoded media, opaque reasoning and provider-executed tools cannot be inspected here.
  blocked_keys={'inlineData','inline_data','fileData','file_data','image_url','input_audio',
    'audio','video','encrypted_content','thoughtSignature','thought_signature','redacted_thinking',
    'cachedContent','cached_content','previous_response_id','conversation','background'}
  def walk(node):
    if isinstance(node,dict):
      if any(k in node and node[k] not in (None,False,[]) for k in blocked_keys):
        raise InspectionError('unsupported_llm_content')
      if node.get('type') in {'image','input_image','input_file','file','computer','computer_use',
          'web_search','web_search_preview','code_interpreter','mcp','server_tool_use','redacted_thinking'}:
        raise InspectionError('unsupported_llm_content')
      for child in node.values():walk(child)
    elif isinstance(node,list):
      for child in node:walk(child)
  walk(value)
  if not response:
    tools=value.get('tools',[])
    if not isinstance(tools,list):raise InspectionError('unsupported_llm_tools')
    for tool in tools:
      if not isinstance(tool,dict):raise InspectionError('unsupported_llm_tools')
      if route.llm_provider=='google' and 'functionDeclarations' in tool:
        if set(tool)!={'functionDeclarations'}:raise InspectionError('unsupported_llm_tools')
      elif route.llm_provider=='anthropic':
        if tool.get('type','custom')!='custom' or not isinstance(tool.get('name'),str):
          raise InspectionError('unsupported_llm_tools')
      elif tool.get('type')!='function':raise InspectionError('unsupported_llm_tools')


def response_timestamp(value, envelope, path, provider):
  """Recognize only native protocol timestamps, never similarly named tool data."""
  if provider not in ("openai", "openrouter", "google") or type(value) is not int:
    return False
  if not 946684800 <= value <= 4102444800:
    return False
  if path == ("created",):
    return envelope.get("object") in ("chat.completion", "chat.completion.chunk")
  if provider == "openai" and path == ("created_at",):
    return envelope.get("object") == "response"
  if (provider == "openai" and path == ("response", "created_at")
      and envelope.get("type") in ("response.created", "response.in_progress",
        "response.completed", "response.failed")):
    return isinstance(envelope.get("response"), dict) and envelope["response"].get("object") == "response"
  return False
