using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeDefinitionCatalogCacheStateTests
{
    [TestMethod]
    public void ConnectionKeyNormalizesBaseUrlAuthorityAndFingerprintsToken()
    {
        var first = NodeDefinitionCatalogCacheState.BuildConnectionKey(
            new EngineHostConnectionSettings
            {
                BaseUrl = " HTTP://LOCALHOST:8000/api ",
                Token = "secret",
            });
        var second = NodeDefinitionCatalogCacheState.BuildConnectionKey(
            new EngineHostConnectionSettings
            {
                BaseUrl = "http://localhost:8000/other",
                Token = "secret",
            });
        var rotated = NodeDefinitionCatalogCacheState.BuildConnectionKey(
            new EngineHostConnectionSettings
            {
                BaseUrl = "http://localhost:8000",
                Token = "rotated",
            });

        Assert.AreEqual(first, second);
        Assert.AreNotEqual(first, rotated);
        Assert.DoesNotContain("secret", first);
    }

    [TestMethod]
    public void CatalogHitRequiresLoadedStateConnectionAndCatalogHash()
    {
        var cacheState = new NodeDefinitionCatalogCacheState();
        var connectionKey = NodeDefinitionCatalogCacheState.BuildConnectionKey(
            new EngineHostConnectionSettings
            {
                BaseUrl = "http://127.0.0.1:8000",
                Token = "secret",
            });
        var catalogState = new NodeDefinitionCatalogStateDto
        {
            CatalogHash = " catalog-1 ",
            ProgramHash = " program-1 ",
        };

        Assert.IsFalse(cacheState.IsCatalogHit(connectionKey, catalogState));
        cacheState.RecordLoadedCatalog(connectionKey, catalogState);

        Assert.IsTrue(
            cacheState.IsCatalogHit(
                connectionKey,
                new NodeDefinitionCatalogStateDto
                {
                    CatalogHash = "catalog-1",
                    ProgramHash = "program-1",
                }));
        Assert.IsFalse(
            cacheState.IsCatalogHit(
                connectionKey,
                new NodeDefinitionCatalogStateDto
                {
                    CatalogHash = "catalog-1",
                    ProgramHash = "program-2",
                }));
        Assert.IsFalse(
            cacheState.IsCatalogHit(
                connectionKey,
                new NodeDefinitionCatalogStateDto { CatalogHash = " " }));
    }

    [TestMethod]
    public void InvalidateCatalogClearsCatalogHit()
    {
        var cacheState = new NodeDefinitionCatalogCacheState();
        var connectionKey = NodeDefinitionCatalogCacheState.BuildConnectionKey(
            new EngineHostConnectionSettings
            {
                BaseUrl = "http://127.0.0.1:8000",
                Token = "secret",
            });
        var catalogState = new NodeDefinitionCatalogStateDto
        {
            CatalogHash = "catalog-1",
        };
        cacheState.RecordLoadedCatalog(connectionKey, catalogState);

        cacheState.InvalidateCatalog();

        Assert.IsFalse(cacheState.IsCatalogHit(connectionKey, catalogState));
    }

    [TestMethod]
    public void SchemaCatalogKeyReportsOnlyActualChanges()
    {
        var cacheState = new NodeDefinitionCatalogCacheState();
        const string connectionKey = "http://127.0.0.1:8000|token:abc";
        var catalogState = new NodeDefinitionCatalogStateDto
        {
            CatalogHash = " catalog-1 ",
            ProgramHash = " program-1 ",
        };

        var first = cacheState.PrepareSchemaCatalogKey(
            connectionKey,
            catalogState,
            out var firstChanged);
        var second = cacheState.PrepareSchemaCatalogKey(
            connectionKey,
            new NodeDefinitionCatalogStateDto
            {
                CatalogHash = "catalog-1",
                ProgramHash = "program-1",
            },
            out var secondChanged);
        var third = cacheState.PrepareSchemaCatalogKey(
            connectionKey,
            new NodeDefinitionCatalogStateDto
            {
                CatalogHash = "catalog-1",
                ProgramHash = "program-2",
            },
            out var thirdChanged);
        var withoutCatalog = cacheState.PrepareSchemaCatalogKey(
            connectionKey,
            null,
            out var withoutCatalogChanged);

        Assert.IsTrue(firstChanged);
        Assert.IsFalse(secondChanged);
        Assert.IsTrue(thirdChanged);
        Assert.IsTrue(withoutCatalogChanged);
        Assert.AreEqual(first, second);
        Assert.IsNotNull(first);
        Assert.IsNull(withoutCatalog);
    }

    [TestMethod]
    public void BuildKeysUseStableNodeIdentity()
    {
        var definition = new NodeDefinitionDto
        {
            NodeType = "GenerateTestTableNode",
            NodeVersion = "1.0",
            ConfigSchemaVersion = "schema-1",
        };

        Assert.AreEqual(
            "GenerateTestTableNode@1.0|schema:schema-1",
            NodeDefinitionCatalogCacheState.BuildSchemaCacheKey(definition));
        Assert.AreEqual(
            ("GenerateTestTableNode", "1.0"),
            NodeDefinitionCatalogCacheState.BuildLookupKey(
                definition.NodeType,
                definition.NodeVersion));
    }
}
