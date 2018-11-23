http = require('http')
fs = require('fs')
path = require('path')

port = process.argv[2] || 8080

var server = http.createServer( (req, res) => {
  if(req.url != path.normalize(req.url)) {
    res.writeHead(400)
    res.end('invalid path')
  } else {
    let filepath = './files/' + path.basename(req.url)
    fs.stat(filepath, (err, stats) => {
      if(err) {
        res.writeHead(404)
        res.end('not found')
      } else {
        fs.createReadStream(filepath)
        .on('error', e => {
          console.error(e)
          res.writeHead(500)
          res.end('server error') })
        .on('open', () => {
          res.writeHead(200, {
            'Content-Type': {'.jpg':'image/jpeg','.webm':'video/webm','.zip':'application/zip','.gz':'application/gzip'}[path.extname(filepath)] || 'text/plain',
            'Content-Length': stats.size,
            'Content-Disposition': 'attachment; filename=' + path.basename(filepath)
          })})
        .pipe(res)
      }
    })
  }
})

server.listen(port, "::1", () => console.log(`Server running at http://::1:${port}/`))
