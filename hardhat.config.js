// Minimum Hardhat config for solidity-docgen to work

require('solidity-docgen');

/**
 * @type import('hardhat/config').HardhatUserConfig
 */
module.exports = {
    solidity: {
        version: "0.8.2",
        settings: {
            optimizer: {
                enabled: true,
                runs: 200,
            },
        },
    },
    docgen: require('./docs/config'),
};
