using System.Linq;
using Avalonia_UI.Api;

namespace Avalonia_UI.Models;

public enum WorkflowRunRuntimeOptionsApplicationState
{
    MainProgramPending,
    ActiveNodesPending,
    FullyApplied,
}

public static class WorkflowRunRuntimeOptionsApplicationStateResolver
{
    public static WorkflowRunRuntimeOptionsApplicationState Resolve(
        WorkflowRunRuntimeOptionsDto state)
    {
        if (state.AppliedVersion < state.RequestedVersion)
        {
            return WorkflowRunRuntimeOptionsApplicationState.MainProgramPending;
        }

        return state.ActiveTaskVersions.Any(
            task => task.RuntimeOptionsVersion < state.RequestedVersion)
            ? WorkflowRunRuntimeOptionsApplicationState.ActiveNodesPending
            : WorkflowRunRuntimeOptionsApplicationState.FullyApplied;
    }
}
