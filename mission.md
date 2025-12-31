i am integrating whatsapp dirrectly to this application so that the processing by gemini can be automatic instead of file upload.



Basically
i need you to add a webhook inpoint /webhook/whatsapp with post method.

this route will receive message object from zapwize api.

the payload ob that ingest message will be as follows.

```
{
  "id": "6232CC122DE27100F01B8E2C11CB4CA2",
  "content": "Text message",
  "number": "22656920671",
  "chatid": "22656920671@s.whatsapp.net",
  "type": "text",
  "isgroup": false,
  "istag": false,
  "from": {
    "fromMe": false,
    "id": "22656920671@s.whatsapp.net",
    "number": "22656920671",
    "pushname": "Louis Bertson",
    "countrycode": "226"
  },
  "group": { "id": "", "name": "" },
  "isviewonce": false
}
```


 you need to create internal workflow so that gemini will provess messages directly as they arrive from any chat or whatsapp groups.
 
