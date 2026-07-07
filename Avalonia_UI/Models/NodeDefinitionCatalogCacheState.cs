using System;
using System.Security.Cryptography;
using System.Text;
using Avalonia_UI.Api;

namespace Avalonia_UI.Models;

public sealed class NodeDefinitionCatalogCacheState
{
    private bool hasLoadedCatalog;
    private string? loadedConnectionKey;
    private string? loadedCatalogHash;
    private string? loadedProgramHash;
    private string? schemaCatalogKey;

    public bool IsCatalogHit(
        string connectionKey,
        NodeDefinitionCatalogStateDto? catalogState)
    {
        var catalogHash = NormalizeToken(catalogState?.CatalogHash);
        if (!hasLoadedCatalog || catalogHash is null)
        {
            return false;
        }

        return string.Equals(loadedConnectionKey, connectionKey, StringComparison.Ordinal)
            && string.Equals(loadedCatalogHash, catalogHash, StringComparison.Ordinal)
            && string.Equals(
                loadedProgramHash,
                NormalizeToken(catalogState?.ProgramHash),
                StringComparison.Ordinal);
    }

    public void RecordLoadedCatalog(
        string connectionKey,
        NodeDefinitionCatalogStateDto? catalogState)
    {
        hasLoadedCatalog = true;
        loadedConnectionKey = connectionKey;
        loadedCatalogHash = NormalizeToken(catalogState?.CatalogHash);
        loadedProgramHash = NormalizeToken(catalogState?.ProgramHash);
    }

    public void InvalidateCatalog()
    {
        hasLoadedCatalog = false;
        loadedConnectionKey = null;
        loadedCatalogHash = null;
        loadedProgramHash = null;
    }

    public string? PrepareSchemaCatalogKey(
        string connectionKey,
        NodeDefinitionCatalogStateDto? catalogState,
        out bool changed)
    {
        var nextSchemaCatalogKey = BuildSchemaCatalogKey(connectionKey, catalogState);
        changed = !string.Equals(
            schemaCatalogKey,
            nextSchemaCatalogKey,
            StringComparison.Ordinal);

        if (changed)
        {
            schemaCatalogKey = nextSchemaCatalogKey;
        }

        return nextSchemaCatalogKey;
    }

    public static string BuildConnectionKey(EngineHostConnectionSettings settings)
    {
        return string.Concat(
            NormalizeBaseUrl(settings.BaseUrl),
            "|token:",
            ComputeTokenFingerprint(settings.Token));
    }

    public static string BuildSchemaCacheKey(NodeDefinitionDto definition)
    {
        return string.Concat(
            definition.NodeType,
            "@",
            definition.NodeVersion,
            "|schema:",
            definition.ConfigSchemaVersion);
    }

    public static (string NodeType, string NodeVersion) BuildLookupKey(
        string nodeType,
        string nodeVersion)
    {
        return (nodeType, nodeVersion);
    }

    private static string? BuildSchemaCatalogKey(
        string connectionKey,
        NodeDefinitionCatalogStateDto? catalogState)
    {
        var catalogHash = NormalizeToken(catalogState?.CatalogHash);
        if (catalogHash is null)
        {
            return null;
        }

        return string.Concat(
            connectionKey,
            "|program:",
            NormalizeToken(catalogState?.ProgramHash) ?? string.Empty,
            "|catalog:",
            catalogHash);
    }

    private static string NormalizeBaseUrl(string baseUrl)
    {
        var trimmed = baseUrl.Trim();
        if (Uri.TryCreate(trimmed, UriKind.Absolute, out var uri))
        {
            return uri.GetLeftPart(UriPartial.Authority)
                .TrimEnd('/')
                .ToLowerInvariant();
        }

        return trimmed.ToLowerInvariant();
    }

    private static string ComputeTokenFingerprint(string token)
    {
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(token));
        return Convert.ToHexString(hash.AsSpan(0, 8)).ToLowerInvariant();
    }

    private static string? NormalizeToken(string? value)
    {
        var trimmed = value?.Trim();
        return string.IsNullOrEmpty(trimmed) ? null : trimmed;
    }
}
