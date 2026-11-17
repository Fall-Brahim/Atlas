const http = require('node:http');

const server = http.createServer((_request, response) => {
  response.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' });
  response.end('Your Node.js application is running.\n');
});

server.listen(process.env.PORT || 3000, '127.0.0.1', () => {
  console.log('Server listening on port ' + (process.env.PORT || 3000));
});
