using System;
using Avalonia_UI.Localization;

namespace Avalonia_UI.Models;

public sealed class WorkflowDefinitionDraftParseCache
{
    private readonly Func<string, DisplayTextFormatter?, WorkflowDefinitionDraftStructure>
        buildStructure;
    private readonly Func<string, WorkflowDefinitionLinearChainAnalysis>
        analyzeLinearChain;
    private readonly Func<string, RuntimeOptionsDraftReadResult>
        readRuntimeOptions;

    private string? cachedDraftJson;
    private WorkflowDefinitionDraftStructure? cachedStructure;
    private bool hasCachedStructure;
    private WorkflowDefinitionLinearChainAnalysis? cachedLinearChainAnalysis;
    private bool hasCachedLinearChainAnalysis;
    private RuntimeOptionsDraftReadResult? cachedRuntimeOptions;
    private bool hasCachedRuntimeOptions;

    public WorkflowDefinitionDraftParseCache()
        : this(
            WorkflowDefinitionDraftStructureBuilder.Build,
            WorkflowDefinitionLinearChainAnalyzer.Analyze,
            RuntimeOptionsDraftReader.Read)
    {
    }

    public WorkflowDefinitionDraftParseCache(
        Func<string, DisplayTextFormatter?, WorkflowDefinitionDraftStructure> buildStructure,
        Func<string, WorkflowDefinitionLinearChainAnalysis> analyzeLinearChain,
        Func<string, RuntimeOptionsDraftReadResult> readRuntimeOptions)
    {
        this.buildStructure = buildStructure;
        this.analyzeLinearChain = analyzeLinearChain;
        this.readRuntimeOptions = readRuntimeOptions;
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
            cachedStructure = buildStructure(workflowDefinitionDraftJson, displayTextFormatter);
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
            cachedLinearChainAnalysis = analyzeLinearChain(workflowDefinitionDraftJson);
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
            cachedRuntimeOptions = readRuntimeOptions(workflowDefinitionDraftJson);
            hasCachedRuntimeOptions = true;
        }

        return cachedRuntimeOptions!;
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

    private void ClearCachedResults()
    {
        cachedStructure = null;
        hasCachedStructure = false;
        cachedLinearChainAnalysis = null;
        hasCachedLinearChainAnalysis = false;
        cachedRuntimeOptions = null;
        hasCachedRuntimeOptions = false;
    }
}
