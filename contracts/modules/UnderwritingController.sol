// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.0;

import "./ComponentController.sol";
import "./PolicyController.sol";
import "../shared/CoreController.sol";

import "@gif-interface/contracts/modules/IUnderwriting.sol";
import "@gif-interface/contracts/components/IComponent.sol";
import "@gif-interface/contracts/components/IRiskpool.sol";


contract UnderwritingController is
    IUnderwriting,
    CoreController
{
    mapping(uint256 => uint256) private _riskpoolIdForProductId;

    ComponentController private _component;
    PolicyController private _policy;

    modifier onlyInstanceOperatorService() {
        require(
            _msgSender() == _getContractAddress("InstanceOperatorService"),
            "ERROR:UWR-001:NOT_INSTANCE_OPERATOR"
        );
        _;
    }

    function _afterInitialize() internal override onlyInitializing {
        _component = ComponentController(_getContractAddress("Component"));
        _policy = PolicyController(_getContractAddress("Policy"));
    }

    function setRiskpoolForProduct(uint256 productId, uint256 riskpoolId) 
        external override
        onlyInstanceOperatorService
    {
        _riskpoolIdForProductId[productId] = riskpoolId;
    }


    function underwrite(bytes32 processId) 
        external override 
        onlyPolicyFlow("Underwriting")
        returns(bool success)
    {
        // check that application is in applied state
        IPolicy.Application memory application = _policy.getApplication(processId);
        require(
            application.state == IPolicy.ApplicationState.Applied,
            "ERROR:UWR-002:INVALID_APPLICATION_STATE"
        );

        // TODO check sum insured can be covered by risk pool
        // 1 get set of nft covering this policy
        // 2 get free capacity per covering nft
        // 3 ensure total free capacity >= sum insure
        // 4 lock capacity in participating nft according to allocated capacity fraction per nft
        // 5 inform that cpacity is available
        // 6 continue here (steps 1-6 to be handled pool internally)

        // TODO need to decide how underwriter gets information about riskpool
        // associated with product that is associated with application
        // registration order 1st risk pool, then product (riskpool id = mandatory constuctor arg)
        // product approval time is time to register relation of product /w risk pool in instance
        // option a) underwriting module keeps track of association
        // option b) in some other module
        // option c) association resolved at runtime via getter function in product
        // lets go for a)
        // - in function approve for a product of the instance operator service the relation
        // of which product id links to which oracle id is stored in underwriting moudle

        // determine riskpool responsible for application
        uint256 riskpoolId = _riskpoolIdForProductId[application.productId];
        IRiskpool riskpool = _getRiskpool(riskpoolId);

        // ask reiskpool to secure application
        bool isSecured = riskpool.collateralizePolicy(processId);
        require(isSecured, "ERROR:UWR-003:RISK_CAPITAL_UNAVAILABLE");

        // // make sure premium amount is available
        // // TODO move this to treasury
        // require(
        //     _token.allowance(policyHolder, address(this)) >= premium, 
        //     "ERROR:TI-3:PREMIUM_NOT_COVERED"
        // );

        // // check how to distribute premium
        // IPricing pricing = getPricingContract();
        // (uint256 feeAmount, uint256 capitalAmount) = pricing.getPremiumSplit(processId);

        // ITreasury treasury = getContract();
        // bool isTransferred = treasury.transferPremium(processId, feeAmount, capitalAmount);
        // require(isTransferred, "ERROR:PFD-003:PREMIUM_TRANSFER_FAILED");

        // final step create policy after successful underwriting
        _policy.setApplicationState(processId, IPolicy.ApplicationState.Underwritten);
        success = true;
    }

    function _getRiskpool(uint256 id) internal view returns (IRiskpool riskpool) {
        IComponent cmp = _component.getComponent(id);
        require(cmp.isRiskpool(), "ERROR:UWR-001:COMPONENT_NOT_RISKPOOL");
        riskpool = IRiskpool(address(cmp));
    }
}
