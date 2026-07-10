using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public sealed class RunMetadataCache
{
    private readonly IRunTableDirectoryService runTableDirectoryService;
    private readonly ILoopRunQueryService loopRunQueryService;
    private readonly Dictionary<NodePageKey, ApiResponseEnvelope<NodeRunPageDto>> nodePages = new();
    private readonly Dictionary<TablePageKey, ApiResponseEnvelope<RunTableDirectoryPageDto>> tablePages = new();
    private readonly Dictionary<IterationKey, ApiResponseEnvelope<List<LoopIterationNodeRunDto>>> iterationNodes = new();
    private readonly Dictionary<IterationTableKey, ApiResponseEnvelope<List<LoopIterationTableRefDto>>> iterationTables = new();

    public RunMetadataCache(
        IRunTableDirectoryService runTableDirectoryService,
        ILoopRunQueryService loopRunQueryService)
    {
        this.runTableDirectoryService = runTableDirectoryService;
        this.loopRunQueryService = loopRunQueryService;
    }

    public async Task<ApiResponseEnvelope<NodeRunPageDto>> GetNodeRunsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int offset = 0,
        int limit = 100,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default)
    {
        var key = new NodePageKey(
            workflowRunId,
            offset,
            limit,
            Join(statuses));
        if (nodePages.TryGetValue(key, out var cached))
        {
            return cached;
        }

        var response = await runTableDirectoryService.ListNodeRunsAsync(
            settings,
            workflowRunId,
            offset,
            limit,
            statuses,
            cancellationToken);
        if (response.Ok)
        {
            nodePages[key] = response;
        }

        return response;
    }

    public async Task<ApiResponseEnvelope<RunTableDirectoryPageDto>> GetTableRefsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int offset = 0,
        int limit = 100,
        string? nodeRunId = null,
        string? tableType = null,
        IReadOnlyCollection<string>? lifecycleStatuses = null,
        string? logicalTableId = null,
        CancellationToken cancellationToken = default)
    {
        var key = new TablePageKey(
            workflowRunId,
            offset,
            limit,
            nodeRunId ?? string.Empty,
            tableType ?? string.Empty,
            Join(lifecycleStatuses),
            logicalTableId ?? string.Empty);
        if (tablePages.TryGetValue(key, out var cached))
        {
            return cached;
        }

        var response = await runTableDirectoryService.ListTableRefsAsync(
            settings,
            workflowRunId,
            offset,
            limit,
            nodeRunId,
            tableType,
            lifecycleStatuses,
            logicalTableId,
            cancellationToken);
        if (response.Ok)
        {
            tablePages[key] = response;
        }

        return response;
    }

    public async Task<ApiResponseEnvelope<List<LoopIterationNodeRunDto>>> GetIterationNodesAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string loopRunId,
        string loopIterationId,
        CancellationToken cancellationToken = default)
    {
        var key = new IterationKey(workflowRunId, loopRunId, loopIterationId);
        if (iterationNodes.TryGetValue(key, out var cached))
        {
            return cached;
        }

        var response = await loopRunQueryService.ListIterationNodesAsync(
            settings,
            workflowRunId,
            loopRunId,
            loopIterationId,
            cancellationToken);
        if (response.Ok)
        {
            iterationNodes[key] = response;
        }

        return response;
    }

    public async Task<ApiResponseEnvelope<List<LoopIterationTableRefDto>>> GetIterationTableRefsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string loopRunId,
        string loopIterationId,
        string? role = null,
        CancellationToken cancellationToken = default)
    {
        var key = new IterationTableKey(
            workflowRunId,
            loopRunId,
            loopIterationId,
            role ?? string.Empty);
        if (iterationTables.TryGetValue(key, out var cached))
        {
            return cached;
        }

        var response = await loopRunQueryService.ListIterationTableRefsAsync(
            settings,
            workflowRunId,
            loopRunId,
            loopIterationId,
            role,
            cancellationToken);
        if (response.Ok)
        {
            iterationTables[key] = response;
        }

        return response;
    }

    public void InvalidateRun(string workflowRunId)
    {
        RemoveWhere(nodePages, key => key.WorkflowRunId == workflowRunId);
        RemoveWhere(tablePages, key => key.WorkflowRunId == workflowRunId);
        RemoveWhere(iterationNodes, key => key.WorkflowRunId == workflowRunId);
        RemoveWhere(iterationTables, key => key.WorkflowRunId == workflowRunId);
    }

    private static string Join(IReadOnlyCollection<string>? values)
    {
        return values is null ? string.Empty : string.Join('\u001f', values);
    }

    private static void RemoveWhere<TKey, TValue>(
        IDictionary<TKey, TValue> values,
        Func<TKey, bool> predicate)
        where TKey : notnull
    {
        var keys = new List<TKey>();
        foreach (var key in values.Keys)
        {
            if (predicate(key))
            {
                keys.Add(key);
            }
        }

        foreach (var key in keys)
        {
            values.Remove(key);
        }
    }

    private sealed record NodePageKey(
        string WorkflowRunId,
        int Offset,
        int Limit,
        string Statuses);

    private sealed record TablePageKey(
        string WorkflowRunId,
        int Offset,
        int Limit,
        string NodeRunId,
        string TableType,
        string LifecycleStatuses,
        string LogicalTableId);

    private sealed record IterationKey(
        string WorkflowRunId,
        string LoopRunId,
        string LoopIterationId);

    private sealed record IterationTableKey(
        string WorkflowRunId,
        string LoopRunId,
        string LoopIterationId,
        string Role);
}
