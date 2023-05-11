// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.18;

import "@openzeppelin/contracts/access/Ownable2Step.sol";

interface IFactory {
    function api_version() external view returns (string memory);
}

contract ReleaseRegistry is Ownable2Step {
    event NewRelease(
        uint256 indexed releaseId,
        address indexed factory,
        string apiVersion
    );

    // The total number of releases that have been deployed
    uint256 public numReleases;

    // Mapping of release id starting at 0 to the address
    // of the corresponding factory for that release.
    mapping(uint256 => address) public factories;

    // Mapping of the API version for a specific release to the
    // place in the order it was released.
    mapping(string => uint256) public releaseTargets;

    /**
    * @notice Returns the latest factory.
    * @dev Throws if no releases are registered yet.
    * @return The address of the factory for the latest release.
     */
    function latestFactory() external view returns (address) {
        return factories[numReleases - 1];
    }

    /**
     * @notice Returns the api version of the latest release.
     * @dev Throws if no releases are registered yet.
     * @return The api version of the latest release.
     */
    function latestRelease() external view returns (string memory) {
        return IFactory(factories[numReleases - 1]).api_version(); // dev: no release
    }

    /**
     * @notice Issue a new release using a deployed factory.
     * @dev Stores the factory address in `factories` and the release
     * target in `releaseTargests` with its associated API version.
     *
     *   Throws if caller isn't `owner`.
     *   Throws if the api version is the same as the previous release.
     *   Emits a `NewRelease` event.
     *
     * @param _factory The factory that will be used create new vaults.
     */
    function newRelease(address _factory) external onlyOwner {
        // Check if the release is different from the current one
        uint256 releaseId = numReleases;

        string memory apiVersion = IFactory(_factory).api_version();

        if (releaseId > 0) {
            // Make sure this isnt the same as the last one
            require(
                keccak256(
                    bytes(IFactory(factories[releaseId - 1]).api_version())
                ) != keccak256(bytes(apiVersion)),
                "VaultRegistry: same api version"
            );
        }

        // Update latest release.
        factories[releaseId] = _factory;

        // Set the api to the target.
        releaseTargets[apiVersion] = releaseId;

        // Increase our number of releases.
        numReleases = releaseId + 1;

        // Log the release for external listeners
        emit NewRelease(releaseId, _factory, apiVersion);
    }
}
