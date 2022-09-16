const fs = require('fs-jetpack')

const main = () => {
  const templateName = process.argv[2]
  const dotName = process.argv[3]
  const tomlName = process.argv[4]

  if (templateName && dotName && tomlName) {
    console.log(`Generating TOML: Template ${templateName}, DOT ${dotName}, output to ${tomlName}`)

    const template = fs.read(templateName)
    const dot = fs.read(dotName)
    const toml = template
      .replace(
        '"""\n"""',
        dot
          .replace('digraph {', '"""')
          .replace('} //digraph', '"""')
          .replaceAll('\\', '\\\\'),
      )
    fs.write(tomlName, toml)
  } else {
    console.log('Usage:');
    console.log('node generate-toml.js <templateName> <.dot name> <output name>');
  }

}

main()
