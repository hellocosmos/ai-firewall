"""Synthetic native provider responses. No remote model calls or real credentials."""
import json


def frame(value,event=None):
  return ((f'event: {event}\n' if event else '')+'data: '+json.dumps(value)+'\n\n').encode()


def reply(provider,path,body):
  text=json.dumps(body)
  if 'fixture-rate-limit' in text:
    return 429,{'content-type':'application/json','retry-after':'1'},json.dumps({'error':{'message':'synthetic rate limit','type':'rate_limit_error','code':'rate_limit_exceeded'}}).encode()
  output='test@example.com' if 'fixture-pii' in text else 'hello'
  stream=body.get('stream',False) or ':streamGenerateContent' in path
  tool='fixture-tool' in text
  model=body.get('model','gemini-test')
  if provider=='google' and '/models/' in path:
    part={'functionCall':{'name':'notes_read','args':{'query':output}}} if tool else {'text':output}
    value={'candidates':[{'index':0,'content':{'role':'model','parts':[part]},'finishReason':'STOP'}],
      'usageMetadata':{'promptTokenCount':2,'candidatesTokenCount':1,'totalTokenCount':3},'modelVersion':model}
    data=frame(value) if stream else json.dumps(value).encode()
  elif provider=='anthropic':
    block={'type':'tool_use','id':'toolu_test','name':'notes_read','input':{'query':output}} if tool else {'type':'text','text':output}
    value={'id':'msg_test','type':'message','role':'assistant','model':model,'content':[block],
      'stop_reason':'tool_use' if tool else 'end_turn','stop_sequence':None,'usage':{'input_tokens':2,'output_tokens':1}}
    if stream:
      start={**value,'content':[],'stop_reason':None,'usage':{'input_tokens':2,'output_tokens':0}}
      first={'type':'tool_use','id':'toolu_test','name':'notes_read','input':{}} if tool else {'type':'text','text':''}
      delta={'type':'input_json_delta','partial_json':json.dumps({'query':output})} if tool else {'type':'text_delta','text':output}
      events=[{'type':'message_start','message':start}, {'type':'content_block_start','index':0,'content_block':first},
        {'type':'content_block_delta','index':0,'delta':delta},{'type':'content_block_stop','index':0},
        {'type':'message_delta','delta':{'stop_reason':value['stop_reason'],'stop_sequence':None},'usage':{'output_tokens':1}},
        {'type':'message_stop'}]
      data=b''.join(frame(e,e['type']) for e in events)
    else:data=json.dumps(value).encode()
  elif path.endswith('/responses'):
    item={'type':'function_call','id':'fc_test','call_id':'call_test','name':'notes_read','arguments':json.dumps({'query':output}),'status':'completed'} if tool else {
      'type':'message','id':'msg_test','role':'assistant','status':'completed','content':[{'type':'output_text','text':output,'annotations':[]}]}
    value={'id':'resp_test','object':'response','created_at':1,'model':model,'status':'completed','output':[item],
      'error':None,'incomplete_details':None,'parallel_tool_calls':True,'tool_choice':'auto','tools':[],
      'usage':{'input_tokens':2,'output_tokens':1,'total_tokens':3}}
    if stream:
      kind='response.function_call_arguments.delta' if tool else 'response.output_text.delta'
      delta={'type':kind,'item_id':item['id'],'output_index':0,'content_index':0,
        'delta':item['arguments'] if tool else output,'sequence_number':1}
      events=[{'type':'response.created','response':{**value,'status':'in_progress','output':[]},'sequence_number':0},
        delta,{'type':'response.completed','response':value,'sequence_number':2}]
      data=b''.join(frame(e,e['type']) for e in events)
    else:data=json.dumps(value).encode()
  else:
    call={'id':'call_test','type':'function','function':{'name':'notes_read','arguments':json.dumps({'query':output})}}
    message={'role':'assistant','content':None,'tool_calls':[call]} if tool else {'role':'assistant','content':output}
    value={'id':'chatcmpl-test','object':'chat.completion','created':1,'model':model,
      'choices':[{'index':0,'message':message,'finish_reason':'tool_calls' if tool else 'stop'}],
      'usage':{'prompt_tokens':2,'completion_tokens':1,'total_tokens':3}}
    if stream:
      delta={'tool_calls':[{'index':0,**call}]} if tool else {'role':'assistant','content':output}
      chunk={k:v for k,v in value.items() if k!='choices'};chunk['object']='chat.completion.chunk'
      data=frame({**chunk,'choices':[{'index':0,'delta':delta,'finish_reason':None}]})
      data+=frame({**chunk,'choices':[{'index':0,'delta':{},'finish_reason':'tool_calls' if tool else 'stop'}]})+b'data: [DONE]\n\n'
    else:data=json.dumps(value).encode()
  return 200,{'content-type':'text/event-stream' if stream else 'application/json'},data
