const fs = require('fs');
const path = require('path');

require('solidity-docgen');

module.exports = {
    solidity: {
        version: '0.8.2',
        settings: {
            optimizer: {
                enabled: true,
                runs: 200,
            },
        },
    },
    docgen: require('./docs/config'),
};

