using System;
using Avalonia_UI.Localization;

namespace Avalonia_UI.Models;

public sealed class WorkflowDefinitionDraftParseCache
{
    private readonly Func<string, WorkflowDefinitionDraftSnapshot> parseSnapshot;
    private readonly Func<
        WorkflowDefinitionDraftSnapshot,
        DisplayTextFormatter?,
        WorkflowDefinitionDraftStructure> buildStructure;
    private readonly Func<
        WorkflowDefinitionDraftSnapshot,
        WorkflowDefinitionLinearChainAnalysis> analyzeLinearChain;
    private readonly Func<
        WorkflowDefinitionDraftSnapshot,
        RuntimeOptionsDraftReadResult> readRuntimeOptions;
    private readonly Func<
        WorkflowDefinitionDraftSnapshot,
        WorkflowLoopRegionDraftReadResult> readLoopRegions;

    private string? cachedDraftJson;
    private WorkflowDefinitionDraftSnapshot? cachedSnapshot;
    private WorkflowDefinitionDraftStructure? cachedStructure;
    private bool hasCachedStructure;
    private WorkflowDefinitionLinearChainAnalysis? cachedLinearChainAnalysis;
    private bool hasCachedLinearChainAnalysis;
    private RuntimeOptionsDraftReadResult? cachedRuntimeOptions;
    private bool hasCachedRuntimeOptions;
    private WorkflowLoopRegionDraftReadResult? cachedLoopRegions;
    private bool hasCachedLoopRegions;

    public WorkflowDefinitionDraftParseCache()
        : this(
            WorkflowDefinitionDraftSnapshot.Parse,
            WorkflowDefinitionDraftStructureBuilder.Build,
            WorkflowDefinitionLinearChainAnalyzer.Analyze,
            RuntimeOptionsDraftReader.Read,
            WorkflowLoopRegionDraftReader.Read)
    {
    }

    public WorkflowDefinitionDraftParseCache(
        Func<string, WorkflowDefinitionDraftSnapshot> parseSnapshot,
        Func<
            WorkflowDefinitionDraftSnapshot,
            DisplayTextFormatter?,
            WorkflowDefinitionDraftStructure> buildStructure,
        Func<
            WorkflowDefinitionDraftSnapshot,
            WorkflowDefinitionLinearChainAnalysis> analyzeLinearChain,
        Func<
            WorkflowDefinitionDraftSnapshot,
            RuntimeOptionsDraftReadResult> readRuntimeOptions,
        Func<
            WorkflowDefinitionDraftSnapshot,
            WorkflowLoopRegionDraftReadResult> readLoopRegions)
    {
        this.parseSnapshot = parseSnapshot;
        this.buildStructure = buildStructure;
        this.analyzeLinearChain = analyzeLinearChain;
        this.readRuntimeOptions = readRuntimeOptions;
        this.readLoopRegions = readLoopRegions;
    }

    public WorkflowDefinitionDraftSnapshot? GetSnapshot(
        string workflowDefinitionDraftJson)
    {
        if (string.IsNullOrWhiteSpace(workflowDefinitionDraftJson))
        {
            return null;
        }

        EnsureCurrentDraftJson(workflowDefinitionDraftJson);
        return GetOrCreateSnapshot(workflowDefinitionDraftJson);
    }

    public WorkflowDefinitionDraftStructure? GetStructure(
        string workflowDefinitionDraftJson,
        DisplayTextFormatter? displayTextFormatter = null)
    {
        if (string.IsNullOrWhiteSpace(workflowDefinitionDraftJson))
        {
            return null;
        }

        EnsureCurrentDraftJson(workflowDefinitionDraftJson);
        if (!hasCachedStructure)
        {
            cachedStructure = buildStructure(
                GetOrCreateSnapshot(workflowDefinitionDraftJson),
                displayTextFormatter);
            hasCachedStructure = true;
        }

        return cachedStructure;
    }

    public WorkflowDefinitionLinearChainAnalysis? GetLinearChainAnalysis(
        string workflowDefinitionDraftJson)
    {
        if (string.IsNullOrWhiteSpace(workflowDefinitionDraftJson))
        {
            return null;
        }

        EnsureCurrentDraftJson(workflowDefinitionDraftJson);
        if (!hasCachedLinearChainAnalysis)
        {
            cachedLinearChainAnalysis = analyzeLinearChain(
                GetOrCreateSnapshot(workflowDefinitionDraftJson));
            hasCachedLinearChainAnalysis = true;
        }

        return cachedLinearChainAnalysis;
    }

    public RuntimeOptionsDraftReadResult GetRuntimeOptions(
        string workflowDefinitionDraftJson)
    {
        if (string.IsNullOrWhiteSpace(workflowDefinitionDraftJson))
        {
            return new RuntimeOptionsDraftReadResult
            {
                Status = RuntimeOptionsDraftReadStatus.Succeeded,
                Draft = new RuntimeOptionsDraft(),
            };
        }

        EnsureCurrentDraftJson(workflowDefinitionDraftJson);
        if (!hasCachedRuntimeOptions)
        {
            cachedRuntimeOptions = readRuntimeOptions(
                GetOrCreateSnapshot(workflowDefinitionDraftJson));
            hasCachedRuntimeOptions = true;
        }

        return cachedRuntimeOptions!;
    }

    public WorkflowLoopRegionDraftReadResult GetLoopRegions(
        string workflowDefinitionDraftJson)
    {
        if (string.IsNullOrWhiteSpace(workflowDefinitionDraftJson))
        {
            return new WorkflowLoopRegionDraftReadResult
            {
                Status = WorkflowLoopRegionDraftReadStatus.Succeeded,
            };
        }

        EnsureCurrentDraftJson(workflowDefinitionDraftJson);
        if (!hasCachedLoopRegions)
        {
            cachedLoopRegions = readLoopRegions(
                GetOrCreateSnapshot(workflowDefinitionDraftJson));
            hasCachedLoopRegions = true;
        }

        return cachedLoopRegions!;
    }

    public void Invalidate()
    {
        cachedDraftJson = null;
        ClearCachedResults();
    }

    private void EnsureCurrentDraftJson(string workflowDefinitionDraftJson)
    {
        if (string.Equals(
                cachedDraftJson,
                workflowDefinitionDraftJson,
                StringComparison.Ordinal))
        {
            return;
        }

        cachedDraftJson = workflowDefinitionDraftJson;
        ClearCachedResults();
    }

    private WorkflowDefinitionDraftSnapshot GetOrCreateSnapshot(
        string workflowDefinitionDraftJson)
    {
        cachedSnapshot ??= parseSnapshot(workflowDefinitionDraftJson);
        return cachedSnapshot;
    }

    private void ClearCachedResults()
    {
        cachedSnapshot = null;
        cachedStructure = null;
        hasCachedStructure = false;
        cachedLinearChainAnalysis = null;
        hasCachedLinearChainAnalysis = false;
        cachedRuntimeOptions = null;
        hasCachedRuntimeOptions = false;
        cachedLoopRegions = null;
        hasCachedLoopRegions = false;
    }
}
